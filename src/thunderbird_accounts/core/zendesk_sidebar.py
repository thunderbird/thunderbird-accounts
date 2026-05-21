import logging
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin

import jwt
import requests
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.models import ZendeskAgentConnection
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.models import Email
from thunderbird_accounts.mail.utils import filter_app_passwords
from thunderbird_accounts.subscription.models import Subscription, Transaction

PUBLIC_KEY_CACHE_KEY = 'zendesk_sidebar_public_key'
PUBLIC_KEY_CACHE_SECONDS = 60 * 60 * 24
ZENDESK_CONNECT_TOKEN_SESSION_KEY = 'zendesk_sidebar_connect_token'
SIDEBAR_VIEW_PERMISSIONS = [
    'authentication.view_user',
    'authentication.view_allowlistentry',
    'mail.view_account',
    'mail.view_email',
    'mail.view_domain',
    'subscription.view_subscription',
    'subscription.view_transaction',
]
ZENDESK_SIDEBAR_PATH_PREFIX = '/zendesk/sidebar/'


def can_view_zendesk_sidebar(user: User) -> bool:
    return user.is_active and user.is_staff and user.has_perms(SIDEBAR_VIEW_PERMISSIONS)


class ZendeskSidebarFrameAncestorsMiddleware:
    """Apply frame policy to all Zendesk sidebar-prefix responses, including middleware fallbacks."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        if request.path.startswith(ZENDESK_SIDEBAR_PATH_PREFIX):
            response.xframe_options_exempt = True
            return _set_zendesk_frame_ancestors(response)
        return response


def get_customer_sidebar_data(email: str | None, via_channel: str | None) -> dict:
    normalized_email = (email or '').strip().lower()
    verified = (via_channel or '').strip().lower() == 'api'

    base_payload = {
        'found': False,
        'requester_email': normalized_email,
        'status': {
            'code': 'not_user',
            'label': 'Not signed up',
            'payment_verification_pending': False,
        },
        'verification': {
            'verified': verified,
            'label': 'Verified' if verified else 'Not verified',
        },
        'profile': None,
        'quota': None,
        'subscription': None,
        'legal': None,
        'allow_list': None,
        'links': {},
        'error': None,
    }

    if not normalized_email:
        base_payload['error'] = 'No requester email is available.'
        return base_payload

    match = _find_customer_match(normalized_email)
    if match['ambiguous']:
        return {
            **base_payload,
            'status': {
                **base_payload['status'],
                'code': 'ambiguous',
                'label': 'Ambiguous match',
            },
            'error': 'This email matches multiple users.',
        }

    user = match['user']
    allow_list_entry = match['allow_list_entry']

    if not user and not allow_list_entry:
        return base_payload

    if allow_list_entry:
        base_payload['allow_list'] = {
            'email': allow_list_entry.email,
            'discount_id': allow_list_entry.discount_id,
        }
        base_payload['links']['allow_list_admin'] = reverse(
            'admin:authentication_allowlistentry_change',
            args=[allow_list_entry.pk],
        )

    if not user and allow_list_entry:
        return {
            **base_payload,
            'found': True,
            'status': {
                **base_payload['status'],
                'code': 'allow_list',
                'label': 'On allow list',
            },
        }

    active_subscription = _get_active_subscription(user)
    status_code = 'user_paid' if active_subscription else 'user_unpaid'
    status_label = 'Paid' if active_subscription else 'User created'

    account = user.account_set.prefetch_related('email_set').first()
    primary_email = _get_primary_email(user, account)

    quota = _build_quota(primary_email, account, fetch_live_usage=bool(active_subscription))
    app_password_set = bool(quota.get('app_password_set')) if quota else False

    stalwart_display_name = quota.get('display_name') if quota else None

    base_payload.update(
        {
            'found': True,
            'status': {
                'code': status_code,
                'label': status_label,
                'payment_verification_pending': user.is_awaiting_payment_verification,
            },
            'profile': _build_profile(user, account, primary_email, app_password_set, stalwart_display_name),
            'quota': quota,
            'subscription': _build_subscription(user, active_subscription),
            'legal': _build_legal_acceptance(user),
            'links': {
                **base_payload['links'],
                **_build_user_links(user, active_subscription),
            },
        }
    )

    return base_payload


def _find_customer_match(email: str) -> dict:
    users_by_pk = {}

    email_record = Email.objects.select_related('account__user').filter(address__iexact=email).first()
    if email_record and email_record.account and email_record.account.user:
        users_by_pk[email_record.account.user.pk] = email_record.account.user

    for user in User.objects.filter(
        Q(username__iexact=email)
        | Q(email__iexact=email)
        | Q(recovery_email__iexact=email)
        | Q(last_used_email__iexact=email)
    ):
        users_by_pk[user.pk] = user

    allow_list_entry = AllowListEntry.objects.select_related('user').filter(email__iexact=email).first()
    if allow_list_entry and allow_list_entry.user:
        users_by_pk[allow_list_entry.user.pk] = allow_list_entry.user

    return {
        'user': next(iter(users_by_pk.values()), None) if len(users_by_pk) <= 1 else None,
        'allow_list_entry': allow_list_entry,
        'ambiguous': len(users_by_pk) > 1,
    }


def _get_active_subscription(user: User) -> Subscription | None:
    return (
        user.subscription_set.filter(status=Subscription.StatusValues.ACTIVE)
        .order_by('-created_at')
        .first()
    )


def _get_primary_email(user: User, account) -> str | None:
    if account:
        primary = account.email_set.filter(type=Email.EmailType.PRIMARY).first()
        if primary:
            return primary.address
    return user.username or user.email


def _build_profile(
    user: User,
    account,
    primary_email: str | None,
    app_password_set: bool,
    stalwart_display_name: str | None,
) -> dict:
    aliases = []
    catch_alls = []
    if account:
        for email in account.email_set.filter(type=Email.EmailType.ALIAS).order_by('address'):
            if email.address.startswith('@'):
                catch_alls.append(email.address)
            else:
                aliases.append(email.address)
    custom_domains = [
        {
            'name': domain.name,
            'status': domain.status,
            'verified_at': _serialize_datetime(domain.verified_at),
            'last_verification_attempt': _serialize_datetime(domain.last_verification_attempt),
        }
        for domain in user.domains.order_by('name')
    ]

    return {
        'primary_email': primary_email,
        'recovery_email': user.recovery_email,
        'display_name': _get_display_name(user, primary_email, stalwart_display_name),
        'app_password_set': app_password_set,
        'aliases': aliases,
        'catch_alls': catch_alls,
        'custom_domains': custom_domains,
        'custom_domain_counts': {
            'verified': sum(domain['status'] == 'verified' for domain in custom_domains),
            'pending': sum(domain['status'] == 'pending' for domain in custom_domains),
        },
    }


def _build_legal_acceptance(user: User) -> dict:
    def legal_document(response: LegalDocumentResponse | None) -> dict:
        return {
            'accepted': bool(response),
            'accepted_at': _serialize_datetime(response.created_at) if response else None,
            'version': response.document.version if response else None,
        }

    responses = (
        LegalDocumentResponse.objects.select_related('document')
        .filter(user=user, action=LegalDocumentResponse.Action.ACCEPTED)
        .order_by('document__document_type', '-created_at')
    )
    accepted_responses = {}
    for response in responses:
        accepted_responses.setdefault(response.document.document_type, response)

    return {
        'terms': legal_document(accepted_responses.get(LegalDocument.DocumentType.TOS)),
        'privacy': legal_document(accepted_responses.get(LegalDocument.DocumentType.PRIVACY)),
    }


def _get_display_name(user: User, primary_email: str | None, stalwart_display_name: str | None) -> str:
    known_emails = {
        (primary_email or '').strip().lower(),
        (user.username or '').strip().lower(),
        (user.email or '').strip().lower(),
        (user.recovery_email or '').strip().lower(),
        (user.last_used_email or '').strip().lower(),
    }

    for display_name in [stalwart_display_name, user.display_name]:
        display_name = (display_name or '').strip()
        if display_name and display_name.lower() not in known_emails:
            return display_name

    return ''


def _build_quota(primary_email: str | None, account, fetch_live_usage: bool) -> dict | None:
    if not primary_email and not account:
        return None

    quota = {
        'used_bytes': None,
        'limit_bytes': account.quota if account else None,
        'used_display': None,
        'limit_display': _format_bytes(account.quota) if account and account.quota is not None else None,
        'available': False,
        'app_password_set': False,
        'display_name': None,
    }

    if not fetch_live_usage:
        return quota

    try:
        stalwart_account = MailClient().get_account(primary_email)
        quota['used_bytes'] = stalwart_account.get('usedQuota')
        quota['limit_bytes'] = stalwart_account.get('quota', quota['limit_bytes'])
        quota['used_display'] = _format_bytes(quota['used_bytes'])
        quota['limit_display'] = _format_bytes(quota['limit_bytes'])
        quota['available'] = True
        quota['app_password_set'] = bool(filter_app_passwords(stalwart_account.get('secrets', [])))
        quota['display_name'] = stalwart_account.get('description')
    except Exception as exc:
        logging.info('Unable to retrieve Zendesk sidebar quota for %s: %s', primary_email, exc)

    return quota


def _build_subscription(user: User, active_subscription: Subscription | None) -> dict | None:
    subscription = active_subscription or user.subscription_set.order_by('-created_at').first()
    if not subscription and not user.plan:
        return None

    total_spend = _get_total_spend(user)
    discount = None
    if subscription and subscription.discount_amount and subscription.discount_type:
        discount = {
            'amount': subscription.discount_amount,
            'type': subscription.discount_type,
        }

    return {
        'status': subscription.status if subscription else None,
        'signup_date': _serialize_datetime(user.date_joined),
        'plan': user.plan.name if user.plan else None,
        'next_renewal_date': _serialize_datetime(subscription.next_billed_at) if subscription else None,
        'discount': discount,
        'total_spend': total_spend,
    }


def _get_total_spend(user: User) -> list[dict]:
    totals = defaultdict(int)
    transactions = Transaction.objects.filter(
        subscription__user=user,
        status__in=[Transaction.StatusValues.PAID, Transaction.StatusValues.COMPLETED],
    )

    for transaction in transactions:
        totals[transaction.currency] += int(transaction.total)

    return [
        {'currency': currency, 'amount': f'{amount / 100:.2f}'}
        for currency, amount in sorted(totals.items())
    ]


def _build_user_links(user: User, active_subscription: Subscription | None) -> dict:
    links = {
        'user_admin': reverse('admin:authentication_user_change', args=[user.pk]),
    }

    subscription = active_subscription or user.subscription_set.order_by('-created_at').first()
    if subscription:
        links['subscription_admin'] = reverse('admin:subscription_subscription_change', args=[subscription.pk])
        if subscription.paddle_id:
            links['paddle_subscription'] = _paddle_vendor_url(f'/subscriptions-v2/{subscription.paddle_id}')
        if subscription.paddle_customer_id:
            links['paddle_customer'] = _paddle_vendor_url(f'/customers-v2/{subscription.paddle_customer_id}')

    return links


def _paddle_vendor_url(path: str) -> str:
    return urljoin(settings.PADDLE_VENDOR_SITE.rstrip('/') + '/', path.lstrip('/'))


def _format_bytes(value: int | None) -> str | None:
    if value is None:
        return None

    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    amount = float(value)
    unit = units[0]
    for unit in units:
        if abs(amount) < 1024 or unit == units[-1]:
            break
        amount /= 1024

    if unit == 'B':
        return f'{int(amount)} {unit}'
    return f'{amount:.1f} {unit}'


def _serialize_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


@csrf_exempt
@xframe_options_exempt
@require_POST
def zendesk_sidebar(request: HttpRequest):
    token = request.POST.get('token')
    if not token:
        return HttpResponseForbidden('Missing Zendesk signed request token.')

    try:
        _validate_zendesk_signed_token(token)
    except Exception as exc:
        logging.warning('Invalid Zendesk signed request token: %s', exc)
        return HttpResponseForbidden('Invalid Zendesk signed request token.')

    return _set_zendesk_frame_ancestors(_render_sidebar(request, token))


@csrf_exempt
@xframe_options_exempt
@require_http_methods(['GET', 'POST'])
def zendesk_sidebar_content(request: HttpRequest):
    request_data = request.POST if request.method == 'POST' else request.GET
    has_session_access = request.user.is_authenticated and can_view_zendesk_sidebar(request.user)

    if request.user.is_authenticated and not has_session_access:
        response = _render_sidebar_content(
            request,
            _build_sidebar_message('Missing required Django permissions for the Zendesk sidebar.'),
        )
        response.status_code = 403
        return response

    if not has_session_access:
        zendesk_token = request_data.get('zendesk_token')
        zendesk_access = _get_zendesk_sidebar_access(zendesk_token)
        if zendesk_access['user'] and zendesk_access['has_access']:
            return _render_sidebar_content(
                request,
                get_customer_sidebar_data(
                    request_data.get('email'),
                    request_data.get('via'),
                ),
            )

        if zendesk_access['user'] and not zendesk_access['has_access']:
            response = _render_sidebar_content(
                request,
                _build_sidebar_message('Missing required Django permissions for the Zendesk sidebar.'),
            )
            response.status_code = 403
            return response

        if zendesk_access['identity']:
            response = _render_sidebar_content(
                request,
                _build_sidebar_message(
                    'Connect your Zendesk account to Thunderbird Pro to use this sidebar.',
                    auth_url=reverse('zendesk_sidebar_connect'),
                    auth_label='Connect Thunderbird Pro',
                    auth_method='post',
                    auth_fields={'zendesk_token': zendesk_token},
                ),
            )
            response.status_code = 401
            return response

        response = _render_sidebar_content(
            request,
            _build_sidebar_message(
                'Sign in to Django in a new tab, then reload Zendesk.',
                auth_url=settings.LOGIN_URL,
                auth_label='Sign in to Django',
            ),
        )
        response.status_code = 401
        return response

    return _render_sidebar_content(
        request,
        get_customer_sidebar_data(
            request_data.get('email'),
            request_data.get('via'),
        ),
    )


@csrf_exempt
@xframe_options_exempt
@require_http_methods(['GET', 'POST'])
def zendesk_sidebar_connect(request: HttpRequest):
    token = request.POST.get('zendesk_token') or request.session.get(ZENDESK_CONNECT_TOKEN_SESSION_KEY)
    identity = _get_zendesk_agent_identity_from_token(token)
    if not identity:
        return HttpResponseForbidden('Invalid Zendesk signed request token.')

    if not request.user.is_authenticated:
        request.session[ZENDESK_CONNECT_TOKEN_SESSION_KEY] = token
        return redirect_to_login(reverse('zendesk_sidebar_connect'), settings.LOGIN_URL)

    if not can_view_zendesk_sidebar(request.user):
        return HttpResponseForbidden('Missing required Django permissions for the Zendesk sidebar.')

    ZendeskAgentConnection.objects.update_or_create(
        zendesk_subdomain=identity['subdomain'],
        zendesk_user_id=identity['user_id'],
        defaults={
            'zendesk_user_email': identity['email'],
            'user': request.user,
        },
    )
    request.session.pop(ZENDESK_CONNECT_TOKEN_SESSION_KEY, None)

    return _set_zendesk_frame_ancestors(
        TemplateResponse(
            request,
            'zendesk/sidebar_connected.html',
            {'identity': identity},
        )
    )


def _build_sidebar_message(
    message: str,
    auth_url: str | None = None,
    auth_label: str | None = None,
    auth_method: str = 'get',
    auth_fields: dict | None = None,
) -> dict:
    return {
        'found': False,
        'requester_email': '',
        'status': {'code': 'auth_required', 'label': 'Authentication required'},
        'verification': {'verified': False, 'label': 'Not verified'},
        'auth_url': auth_url,
        'auth_label': auth_label or 'Sign in to Django',
        'auth_method': auth_method,
        'auth_fields': auth_fields or {},
        'error': message,
    }


def _render_sidebar_content(request: HttpRequest, data: dict) -> TemplateResponse:
    response = TemplateResponse(
        request,
        'zendesk/sidebar_content.html',
        {'data': data},
    )
    response['Referrer-Policy'] = 'no-referrer'
    return _set_zendesk_frame_ancestors(response)


def _render_sidebar(request: HttpRequest, token: str):
    return TemplateResponse(request, 'zendesk/sidebar.html', {'zendesk_token': token})


def _set_zendesk_frame_ancestors(response: HttpResponse) -> HttpResponse:
    ancestors = ["'self'"]
    ancestors.append(f'https://mozilla.kewis.ch')
    ancestors.extend(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []))
    if settings.ZENDESK_SUBDOMAIN:
        ancestors.append(f'https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com')

    frame_ancestors = f'frame-ancestors {" ".join(dict.fromkeys(ancestors))}'
    existing_csp = response.get('Content-Security-Policy', '')
    preserved_directives = [
        directive.strip()
        for directive in existing_csp.split(';')
        if directive.strip() and not directive.strip().lower().startswith('frame-ancestors')
    ]
    response['Content-Security-Policy'] = '; '.join([*preserved_directives, frame_ancestors])
    return response


def _get_zendesk_sidebar_access(token: str | None) -> dict:
    identity = _get_zendesk_agent_identity_from_token(token)
    if not identity:
        return {'identity': None, 'user': None, 'has_access': False}

    connection = (
        ZendeskAgentConnection.objects.select_related('user')
        .filter(
            zendesk_subdomain=identity['subdomain'],
            zendesk_user_id=identity['user_id'],
        )
        .first()
    )
    user = connection.user if connection else None
    return {
        'identity': identity,
        'user': user,
        'has_access': bool(user and can_view_zendesk_sidebar(user)),
    }


def _get_zendesk_agent_identity_from_token(token: str | None) -> dict | None:
    if not token:
        return None

    try:
        claims = _validate_zendesk_signed_token(token)
    except Exception as exc:
        logging.warning('Invalid Zendesk sidebar connection token: %s', exc)
        return None

    return _extract_zendesk_agent_identity(claims)


def _extract_zendesk_agent_identity(claims: dict) -> dict | None:
    subdomain = _extract_zendesk_subdomain(claims)
    user_id = _first_claim_value(
        claims,
        [
            ('sub',),
            ('user_id',),
            ('zendesk_user_id',),
            ('context', 'user_id'),
            ('context', 'user', 'id'),
            ('context', 'currentUser', 'id'),
            ('context', 'current_user', 'id'),
        ],
    )
    email = _first_claim_value(
        claims,
        [
            ('email',),
            ('user_email',),
            ('zendesk_user_email',),
            ('context', 'user_email'),
            ('context', 'user', 'email'),
            ('context', 'currentUser', 'email'),
            ('context', 'current_user', 'email'),
        ],
    )

    if not subdomain or not user_id:
        return None

    return {
        'subdomain': str(subdomain),
        'user_id': str(user_id),
        'email': str(email or ''),
    }


def _extract_zendesk_subdomain(claims: dict) -> str | None:
    configured_subdomain = getattr(settings, 'ZENDESK_SUBDOMAIN', None)
    if configured_subdomain:
        return configured_subdomain

    issuer = str(claims.get('iss') or '').removeprefix('https://')
    if issuer.endswith('.zendesk.com'):
        return issuer.removesuffix('.zendesk.com')
    return None


def _first_claim_value(claims: dict, paths: list[tuple[str, ...]]):
    for path in paths:
        value = claims
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value not in [None, '']:
            return value
    return None


def _validate_zendesk_signed_token(token: str) -> dict:
    public_key = _get_zendesk_public_key()
    claims = jwt.decode(
        token,
        public_key,
        algorithms=['RS256'],
        options={'verify_aud': False},
    )

    expected_issuer = f'{settings.ZENDESK_SUBDOMAIN}.zendesk.com'
    issuer = claims.get('iss', '')
    if expected_issuer and issuer not in [expected_issuer, f'https://{expected_issuer}']:
        raise ValueError('Unexpected Zendesk issuer.')

    context = claims.get('context') or {}
    if context.get('product') != 'support' or context.get('location') != 'ticket_sidebar':
        raise ValueError('Unexpected Zendesk app context.')

    return claims


def _get_zendesk_public_key() -> str:
    public_key = cache.get(PUBLIC_KEY_CACHE_KEY)
    if public_key:
        return public_key

    if not settings.ZENDESK_SUBDOMAIN or not settings.ZENDESK_APP_ID:
        raise ValueError('Zendesk subdomain and app id are required for signed sidebar validation.')

    response = requests.get(
        f'https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/apps/{settings.ZENDESK_APP_ID}/public_key.pem',
        auth=(f'{settings.ZENDESK_USER_EMAIL}/token', settings.ZENDESK_API_TOKEN),
        timeout=10,
    )
    response.raise_for_status()
    public_key = response.text
    cache.set(PUBLIC_KEY_CACHE_KEY, public_key, PUBLIC_KEY_CACHE_SECONDS)
    return public_key

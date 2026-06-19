import json
import logging
from collections import defaultdict
from datetime import datetime
from functools import cache
from urllib.parse import urljoin

import jwt
from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.utils import get_absolute_url
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.models import Email
from thunderbird_accounts.mail.utils import filter_app_passwords
from thunderbird_accounts.subscription.models import Subscription, Transaction

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

    return _set_zendesk_frame_ancestors(_render_sidebar(request))


@csrf_exempt
@xframe_options_exempt
@require_http_methods(['GET', 'POST'])
def zendesk_sidebar_content(request: HttpRequest):
    request_data = _get_request_data(request)
    has_session_access = request.user.is_authenticated and can_view_zendesk_sidebar(request.user)

    if request.user.is_authenticated and not has_session_access:
        response = _render_sidebar_content(
            request,
            _build_sidebar_message('Missing required Django permissions for the Zendesk sidebar.'),
        )
        response.status_code = 403
        return response

    if not has_session_access:
        oauth_access = _get_zendesk_oauth_access(request)
        if oauth_access['user'] and oauth_access['has_access']:
            return _render_sidebar_content(
                request,
                get_customer_sidebar_data(
                    request_data.get('email'),
                    request_data.get('via'),
                ),
            )

        message = oauth_access['error'] or 'Authorize Thundermail in the Zendesk app settings, then reload Zendesk.'
        response = _render_sidebar_content(request, _build_sidebar_message(message))
        response.status_code = 403 if oauth_access['user'] else 401
        return response

    return _render_sidebar_content(
        request,
        get_customer_sidebar_data(
            request_data.get('email'),
            request_data.get('via'),
        ),
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


def _render_sidebar(request: HttpRequest):
    return TemplateResponse(
        request,
        'zendesk/sidebar.html',
        {'content_url': get_absolute_url(reverse('zendesk_sidebar_content'))},
    )


def _set_zendesk_frame_ancestors(response: HttpResponse) -> HttpResponse:
    ancestors = ["'self'"]
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


def _get_request_data(request: HttpRequest) -> dict:
    if request.method == 'GET':
        return request.GET

    content_type = request.headers.get('Content-Type', '')
    if content_type.startswith('application/json'):
        try:
            return json.loads(request.body.decode() or '{}')
        except json.JSONDecodeError:
            return {}

    return request.POST


def _get_zendesk_oauth_access(request: HttpRequest) -> dict:
    token = _get_bearer_token(request)
    if not token:
        return {'claims': None, 'user': None, 'has_access': False, 'error': None}

    try:
        claims = _validate_zendesk_oauth_token(token)
    except (jwt.PyJWTError, ValueError) as exc:
        logging.warning('Invalid Zendesk sidebar OAuth token: %s', exc)
        return {'claims': None, 'user': None, 'has_access': False, 'error': None}

    sub = claims.get('sub')
    if not sub:
        return {'claims': claims, 'user': None, 'has_access': False, 'error': None}

    user = User.objects.filter(oidc_id=sub).first()
    if not user:
        email = claims.get('email') or 'this Keycloak user'
        return {
            'claims': claims,
            'user': None,
            'has_access': False,
            'error': f'No Thundermail staff account is linked to {email}.',
        }

    has_access = can_view_zendesk_sidebar(user)
    return {
        'claims': claims,
        'user': user,
        'has_access': has_access,
        'error': None if has_access else 'Missing required Django permissions for the Zendesk sidebar.',
    }


def _get_bearer_token(request: HttpRequest) -> str | None:
    authorization = request.headers.get('Authorization', '')
    if not authorization.lower().startswith('bearer '):
        return None
    return authorization[7:].strip() or None


def _validate_zendesk_oauth_token(token: str) -> dict:
    issuer = _required_setting('ZENDESK_OAUTH_ISSUER')
    audience = _required_setting('ZENDESK_OAUTH_AUDIENCE')
    client_id = _required_setting('ZENDESK_OAUTH_CLIENT_ID')
    claims = jwt.decode(
        token,
        _get_zendesk_oauth_signing_key(token),
        algorithms=['RS256'],
        audience=audience,
        issuer=issuer,
        options={'require': ['exp', 'iat', 'sub']},
    )

    if claims.get('azp') != client_id:
        raise jwt.InvalidTokenError('Unexpected OAuth authorized party.')

    return claims


def _get_zendesk_oauth_signing_key(token: str):
    jwks_endpoint = _required_setting('ZENDESK_OAUTH_JWKS_ENDPOINT')
    return _get_jwks_client(jwks_endpoint).get_signing_key_from_jwt(token).key


@cache
def _get_jwks_client(jwks_endpoint: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_endpoint)


def _validate_zendesk_signed_token(token: str) -> dict:
    zendesk_subdomain = _required_setting('ZENDESK_SUBDOMAIN')
    public_key = _required_setting('ZENDESK_APP_PUBLIC_KEY').replace('\\n', '\n')
    audience = _required_setting('ZENDESK_APP_AUDIENCE')
    claims = jwt.decode(
        token,
        public_key,
        algorithms=['RS256'],
        audience=audience,
        options={'require': ['exp', 'iat']},
    )

    expected_issuer = f'{zendesk_subdomain}.zendesk.com'
    issuer = claims.get('iss', '')
    if expected_issuer and issuer not in [expected_issuer, f'https://{expected_issuer}']:
        raise ValueError('Unexpected Zendesk issuer.')

    context = claims.get('context') or {}
    if context.get('product') != 'support' or context.get('location') != 'ticket_sidebar':
        raise ValueError('Unexpected Zendesk app context.')

    return claims


def _required_setting(name: str) -> str:
    value = getattr(settings, name, None)
    if not value:
        raise ValueError(f'{name} is required for Zendesk sidebar authentication.')
    return value

"""Customer support lookup API.

This module powers the authenticated support customer endpoint used by support
tools such as Zendesk. It deliberately builds the response in permission-gated
sections so a staff viewer only receives the customer data their Django model
permissions allow them to see.
"""

import logging
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from thunderbird_accounts.authentication.models import AllowListEntry, User
from thunderbird_accounts.core.utils import get_absolute_url
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.models import Email
from thunderbird_accounts.mail.utils import filter_app_passwords
from thunderbird_accounts.subscription.models import Subscription, Transaction


def get_customer_support_data(email: str | None, viewer: User | None = None) -> dict:
    """Return a permission-filtered support summary for the customer email."""
    normalized_email = (email or '').strip().lower()

    if not normalized_email or viewer is None or not viewer.is_active or not viewer.is_staff:
        return {'error': 'Customer is not available.'}

    match = _find_customer_match(normalized_email)
    if match['ambiguous']:
        return {'error': 'This email matches multiple users'}

    user = match['user']
    allow_list_entry = match['allow_list_entry']
    found = False
    links = {}
    subscription = None
    profile = None
    quota = None
    legal = None
    allow_list = None

    if allow_list_entry and viewer.has_perm('authentication.view_allowlistentry'):
        allow_list = {
            'email': allow_list_entry.email,
            'discount_id': allow_list_entry.discount_id,
        }
        links['allow_list_admin'] = get_absolute_url(
            reverse(
                'admin:authentication_allowlistentry_change',
                args=[allow_list_entry.pk],
            )
        )
        found = True

    if user:
        can_view_profile = (
            viewer.has_perm('authentication.view_user')
            and viewer.has_perm('mail.view_account')
            and viewer.has_perm('mail.view_email')
        )
        can_view_subscription = (
            can_view_profile
            and viewer.has_perm('subscription.view_plan')
            and viewer.has_perm('subscription.view_subscription')
            and viewer.has_perm('subscription.view_transaction')
        )

        active_subscription = (
            user.subscription_set.filter(status=Subscription.StatusValues.ACTIVE).order_by('-created_at').first()
        )

        if can_view_profile:
            account = user.account_set.prefetch_related('email_set').first()
            primary_email = _get_primary_email(account)
            if primary_email is None and can_view_profile:
                primary_email = user.username or user.email

            stalwart_data = _get_stalwart_data(primary_email, bool(active_subscription))
            quota = _build_quota(stalwart_data, account)

            profile = _build_profile(user, account, primary_email, bool(stalwart_data['app_password_set']), viewer)
            links['user_admin'] = get_absolute_url(reverse('admin:authentication_user_change', args=[user.pk]))

            if viewer.has_perm('legal.view_legaldocumentresponse') and viewer.has_perm('legal.view_legaldocument'):
                legal = _build_legal_acceptance(user)

            found = True

        if can_view_profile and can_view_subscription:
            sub_record = active_subscription or user.subscription_set.order_by('-created_at').first()

            if sub_record or user.plan:
                subscription = {
                    # User and plan information
                    'signup_date': _serialize_datetime(user.date_joined),
                    'total_spend': _get_total_spend(user),
                    'pending_verification': user.is_awaiting_payment_verification,
                    'plan': user.plan.name if user.plan else None,
                    # Subscription record information
                    'status': sub_record.status if sub_record else None,
                    'next_renewal_date': _serialize_datetime(sub_record.next_billed_at) if sub_record else None,
                    'discount': {
                        'amount': sub_record.discount_amount,
                        'type': sub_record.discount_type,
                    }
                    if sub_record and sub_record.discount_amount and sub_record.discount_type
                    else None,
                }

                links.update(_build_subscription_links(user, sub_record))
                found = True

    return {
        'found': found,
        'profile': profile,
        'quota': quota,
        'subscription': subscription,
        'legal': legal,
        'allow_list': allow_list,
        'links': links,
        'error': None,
    }


def _find_customer_match(email: str) -> dict:
    """Find one customer user and any allow-list entry matching ``email``.

    A single address can appear in several fields and tables, so matches are
    deduplicated by user primary key. If the same email points to multiple users
    the result is marked ambiguous and no user is returned.
    """
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


def _get_primary_email(account) -> str | None:
    """Return the account's primary email address, if one exists."""
    if not account:
        return None

    primary = account.email_set.filter(type=Email.EmailType.PRIMARY).first()
    if primary:
        return primary.address

    return None


def _build_profile(
    user: User,
    account,
    primary_email: str | None,
    app_password_set: bool,
    viewer: User,
) -> dict:
    """Build the profile section exposed to fully authorized staff viewers."""
    aliases = []
    catch_alls = []
    if account:
        for email in account.email_set.filter(type=Email.EmailType.ALIAS).order_by('address'):
            if email.address.startswith('@'):
                catch_alls.append(email.address)
            else:
                aliases.append(email.address)

    return {
        'primary_email': primary_email,
        'recovery_email': user.recovery_email,
        'display_name': _get_display_name(user, primary_email),
        'app_password_set': app_password_set,
        'aliases': aliases,
        'catch_alls': catch_alls,
        'custom_domains': [
            {
                'name': domain.name,
                'status': domain.status,
                'verified_at': _serialize_datetime(domain.verified_at),
                'last_verification_attempt': _serialize_datetime(domain.last_verification_attempt),
            }
            for domain in user.domains.order_by('name')
        ]
        if viewer.has_perm('mail.view_domain')
        else None,
    }


def _build_legal_acceptance(user: User) -> dict | None:
    """Return the latest accepted legal document response per document type."""

    def legal_document(response: LegalDocumentResponse | None) -> dict:
        document = {
            'accepted': bool(response),
            'accepted_at': _serialize_datetime(response.created_at) if response else None,
        }
        document['version'] = response.document.version if response else None
        return document

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


def _get_display_name(user: User, primary_email: str | None) -> str:
    """Return a display name only when it is distinct from known email values."""
    known_emails = {
        (primary_email or '').strip().lower(),
        (user.username or '').strip().lower(),
        (user.email or '').strip().lower(),
        (user.recovery_email or '').strip().lower(),
        (user.last_used_email or '').strip().lower(),
    }

    display_name = (user.display_name or '').strip()
    if display_name and display_name.lower() not in known_emails:
        return display_name

    return ''


def _build_quota(stalwart_data: dict, account) -> dict | None:
    """Build quota data, falling back to the local account quota when needed."""
    return {
        'used_bytes': stalwart_data['used_bytes'],
        'limit_bytes': stalwart_data['limit_bytes'] or (account.quota if account else None),
    }


def _get_stalwart_data(primary_email: str | None, has_active_subscription: bool) -> dict | None:
    """Fetch live quota and app-password state for active subscribers."""
    stalwart_data = {'used_bytes': None, 'limit_bytes': None, 'app_password_set': None}

    if has_active_subscription:
        try:
            stalwart_account = MailClient().get_account(primary_email)
            stalwart_data['used_bytes'] = stalwart_account.get('usedQuota')
            stalwart_data['limit_bytes'] = stalwart_account.get('quota')
            stalwart_data['app_password_set'] = bool(filter_app_passwords(stalwart_account.get('secrets', [])))
        except Exception as exc:
            logging.info('Unable to retrieve support customer quota for %s: %s', primary_email, exc)

    return stalwart_data


def _get_total_spend(user: User) -> list[dict]:
    """Sum paid and completed Paddle transactions by currency."""
    totals = defaultdict(int)
    transactions = Transaction.objects.filter(
        subscription__user=user,
        status__in=[Transaction.StatusValues.PAID, Transaction.StatusValues.COMPLETED],
    )

    for transaction in transactions:
        totals[transaction.currency] += int(transaction.total)

    return [{'currency': currency, 'amount': f'{amount / 100:.2f}'} for currency, amount in sorted(totals.items())]


def _build_subscription_links(user: User, active_subscription: Subscription | None) -> dict:
    """Build Django admin and Paddle vendor links for the relevant subscription."""
    links = {}
    subscription = active_subscription or user.subscription_set.order_by('-created_at').first()
    if subscription:
        links['subscription_admin'] = get_absolute_url(
            reverse('admin:subscription_subscription_change', args=[subscription.pk])
        )
        if subscription.paddle_id:
            links['paddle_subscription'] = _paddle_vendor_url(f'/subscriptions-v2/{subscription.paddle_id}')
        if subscription.paddle_customer_id:
            links['paddle_customer'] = _paddle_vendor_url(f'/customers-v2/{subscription.paddle_customer_id}')

    return links


def _paddle_vendor_url(path: str) -> str:
    """Return an absolute Paddle vendor URL for ``path``."""
    return urljoin(settings.PADDLE_VENDOR_SITE.rstrip('/') + '/', path.lstrip('/'))


def _serialize_datetime(value: datetime | None) -> str | None:
    """Serialize datetimes with ISO 8601, preserving ``None`` values."""
    if not value:
        return None
    return value.isoformat()


class SupportCustomerThrottle(UserRateThrottle):
    scope = 'support_customer_api'


@api_view(['POST'])
@authentication_classes([OIDCAuthentication])
@permission_classes([IsAuthenticated])
@throttle_classes([SupportCustomerThrottle])
def zendesk_sidebar_customer_api(request: Request):
    """Authenticated API endpoint for support customer lookups."""
    if not request.user.is_active or not request.user.is_staff:
        return Response({'detail': 'You do not have permission to view support customer data.'}, status=403)

    return Response(
        get_customer_sidebar_data(
            request.data.get('email'),
            request.user,
        )
    )

import datetime
import json
import logging
import secrets
import requests

import requests.exceptions
import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
from thunderbird_accounts.authentication.reserved import is_reserved
from thunderbird_accounts.mail.clients import DomainVerificationErrors, MailClient, StaleDNSRecordCode
from thunderbird_accounts.mail.dkim import build_customer_dkim_cname_records
from thunderbird_accounts.mail.exceptions import (
    AccessTokenNotFound,
    AccountNotFoundError,
    DomainAlreadyExistsError,
    DomainNotFoundError,
    EmailNotValidError,
)
from thunderbird_accounts.mail.dns import check_stale_dns_records
from thunderbird_accounts.mail.utils import (
    filter_app_passwords,
    is_address_taken,
    validate_email,
)

from thunderbird_accounts.mail.models import Account, Email, Domain
from thunderbird_accounts.mail import tasks as mail_tasks
from thunderbird_accounts.mail import utils


def _critical_errors_from_stale_dns_records(stale_dns_records: list[dict]) -> list[DomainVerificationErrors]:
    stale_record_codes = {record.get('code') for record in stale_dns_records}
    critical_errors = []

    if StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value in stale_record_codes:
        critical_errors.append(DomainVerificationErrors.AUTODISCOVER_RECORD_FOUND)
    if StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value in stale_record_codes:
        critical_errors.append(DomainVerificationErrors.AUTODISCOVER_SRV_RECORD_FOUND)

    return critical_errors


def _capture_domain_exception(exception: Exception, domain: Domain, *, phase: str):
    sentry_sdk.set_context(
        'domain',
        {
            'phase': phase,
            'domain_name': domain.name,
            'domain_status': domain.status,
        },
    )
    sentry_sdk.capture_exception(exception)


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def app_password_set(request: HttpRequest):
    """Sets an app password for a remote Stalwart account"""

    if not request.user.has_active_subscription:
        return JsonResponse(
            {'success': False, 'error': str(_('An active subscription is required to set an app password.'))},
            status=403,
        )

    try:
        data = json.loads(request.body)
        new_password = data.get('password')
        label = data.get('name')

        if not new_password or not label:
            return JsonResponse({'success': False, 'error': str(_('Label and password are required'))}, status=400)

        stalwart_client = MailClient()

        email_user = stalwart_client.get_account(request.user.stalwart_primary_email)

        # Find and delete all previously existing app passwords, keeping
        # the one created by the Appointment CalDAV setup flow.
        for secret in filter_app_passwords(email_user.get('secrets', [])):
            stalwart_client.delete_app_password(request.user.stalwart_primary_email, secret)

        # Create and save the new app password
        new_secret = utils.save_app_password(label, new_password)
        stalwart_client.save_app_password(request.user.stalwart_primary_email, new_secret)

        return JsonResponse({'success': True, 'message': str(_('Password set successfully'))})
    except AccountNotFoundError:
        return JsonResponse(
            {'success': False, 'error': str(_('Could not connect to Thundermail, please try again later.'))}, status=500
        )
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': str(_('Invalid request data'))}, status=400)
    except Exception as e:
        logging.error(f'Error setting app password: {e}')
        return JsonResponse(
            {'success': False, 'error': str(_('An error occurred while setting the password. Please try again.'))},
            status=500,
        )


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('display-name')
def display_name_set(request: HttpRequest):
    """Sets a display name for a remote Stalwart account"""

    try:
        data = json.loads(request.body)
        display_name = data.get('display-name')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': str(_('Invalid request data'))}, status=400)

    if not display_name:
        return JsonResponse({'success': False, 'error': str(_('Display name is required'))}, status=400)

    stalwart_client = MailClient()
    try:
        stalwart_client.update_individual(request.user.stalwart_primary_email, full_name=display_name)
    except AccountNotFoundError:
        messages.error(request, _('Could not connect to Thundermail, please try again later.'))

    return JsonResponse({'success': True, 'message': str(_('Display name set successfully'))})


@login_required
@require_http_methods(['POST'])
def create_custom_domain(request: HttpRequest):
    """Creates a custom domain for the user"""
    data = json.loads(request.body)
    domain_name = data.get('domain-name')

    if not domain_name:
        return JsonResponse({'success': False, 'error': _('Domain name is required')}, status=400)

    domain_name = domain_name.lower()

    custom_domain_count = request.user.domains.count()

    if custom_domain_count >= request.user.plan.mail_domain_count:
        return JsonResponse(
            {'success': False, 'error': _('You have reached the maximum number of custom domains')}, status=400
        )

    try:
        stalwart_client = MailClient()

        try:
            domain = stalwart_client.get_domain(domain_name)
            if domain:
                raise DomainAlreadyExistsError(domain_name)
        except DomainNotFoundError:
            pass

        # If request fails the dkim will hit our general exception catch
        # we want this to happen before the local reference (Domain model) is created
        # so we're not missing any dkim records in the dns record list.
        stalwart_client.create_dkim(domain_name)
        mail_tasks.publish_hosted_dkim_dns_records.delay(domain_name)

        try:
            Domain.objects.create(name=domain_name, user=request.user, stalwart_id=None, stalwart_created_at=None)
        except IntegrityError:
            raise DomainAlreadyExistsError(domain_name)

    except DomainAlreadyExistsError:
        return JsonResponse(
            {
                'success': False,
                'error': _('This domain is already configured.'),
                # This error returns a code so that the frontend can show a i18n message with a link to contact page
                'code': 'domain_already_configured',
            },
            status=400,
        )

    except Exception as e:
        logging.error(f'Error creating custom domain: {e}')
        return JsonResponse(
            {'success': False, 'error': 'An error occurred while creating the custom domain. Please try again later.'},
            status=500,
        )

    return JsonResponse({'success': True})


@login_required
@require_http_methods(['GET'])
def get_dns_records(request: HttpRequest):
    """Gets the DNS records for a custom domain"""
    domain = request.user.domains.get(name=request.GET.get('domain-name'))
    if not domain:
        return JsonResponse({'success': False, 'error': _('Domain not found')}, status=404)

    try:
        stalwart_client = MailClient()
        dns_records = stalwart_client.build_expected_dns_records(domain.name)

        return JsonResponse(
            {
                'success': True,
                'critical_errors': [],
                'warnings': [],
                'dns_records': dns_records,
                'stale_dns_records': [],
                'dkim_cname_records': build_customer_dkim_cname_records(domain.name),
            }
        )
    except Exception as e:
        logging.error(f'Error getting DNS records: {e}')
        return JsonResponse(
            {'success': False, 'error': 'An error occurred while getting the DNS records. Please try again later.'},
            status=500,
        )


@login_required
@require_http_methods(['POST'])
def verify_custom_domain(request: HttpRequest):
    """Verifies a custom domain"""
    data = json.loads(request.body)
    domain_name = data.get('domain-name')
    if not domain_name:
        return JsonResponse({'success': False, 'error': _('Domain name is required')}, status=400)

    domain_name = domain_name.lower()

    domain = request.user.domains.get(name=domain_name)
    if not domain:
        return JsonResponse({'success': False, 'error': _('Domain not found')}, status=404)

    now = datetime.datetime.now(datetime.UTC)

    try:
        stalwart_client = MailClient()

        dns_check = stalwart_client.check_domain_dns(domain.name)
        if settings.CUSTOM_DOMAINS_DO_VERIFY:
            is_verified = dns_check['is_verified']
            critical_errors = dns_check['critical_errors']
            warnings = dns_check['warnings']
        else:
            is_verified = True
            critical_errors = []
            warnings = [_('Custom domain DNS verification disabled. Automatically verified domain.')]

        domain.last_verification_attempt = now

        dns_records = dns_check['dns_records']
        stale_dns_records = check_stale_dns_records(domain.name)
        stale_dns_critical_errors = _critical_errors_from_stale_dns_records(stale_dns_records)
        for critical_error in stale_dns_critical_errors:
            if critical_error not in critical_errors:
                critical_errors.append(critical_error)

        if stale_dns_critical_errors:
            is_verified = False

        response_data = {
            'critical_errors': critical_errors,
            'warnings': warnings,
            'dns_records': dns_records,
            'stale_dns_records': stale_dns_records,
        }

        # If we're verified via dns check
        if is_verified:
            try:
                stalwart_resp = stalwart_client.get_domain(domain_name)
            except DomainNotFoundError:
                stalwart_resp = None

            # Only roll through these steps if we're not already verified OR stalwart doesn't have our domain
            if domain.status != Domain.DomainStatus.VERIFIED or not stalwart_resp:
                domain.status = Domain.DomainStatus.VERIFIED
                domain.verified_at = now

                # Fetch or create a domain on Stalwart's end, and retrieve the domain_id
                if stalwart_resp:
                    domain_id = stalwart_resp.get('id')
                else:
                    domain_id = stalwart_client.create_domain(domain_name)

                # Ensure missing DKIM selectors without replacing keys created at domain-add time.
                stalwart_client.ensure_dkim(domain_name)

                mail_tasks.publish_hosted_dkim_dns_records.delay(domain_name)
                if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
                    stalwart_client.activate_pending_dkim_signatures(domain_name)

                if domain_id:
                    domain.stalwart_id = domain_id
                else:
                    logging.error(f'There was a problem saving the domain id for {domain.name} / {domain.uuid}')

                domain.stalwart_created_at = datetime.datetime.now(datetime.UTC)
                domain.save()

            return JsonResponse({'success': True, **response_data})
        else:
            domain.status = Domain.DomainStatus.FAILED
            domain.save()

            return JsonResponse({'success': False, **response_data})
    except Exception as e:
        domain.status = Domain.DomainStatus.FAILED
        domain.save()

        logging.error(f'Error verifying domain: {e}')
        return JsonResponse(
            {'success': False, 'error': 'An error occurred while verifying the domain. Please try again later.'},
            status=500,
        )


@login_required
@require_http_methods(['DELETE'])
def remove_custom_domain(request: HttpRequest):
    """Removes a custom domain"""
    data = json.loads(request.body)
    domain_name = data.get('domain-name')

    if not domain_name:
        return JsonResponse({'success': False, 'error': _('Domain name is required')}, status=400)

    domain_name = domain_name.lower()
    domain = request.user.domains.get(name=domain_name)
    if not domain:
        return JsonResponse({'success': False, 'error': _('Domain not found')}, status=404)

    # Check if we have any aliases for that domain setup
    try:
        account = Account.objects.get(user=request.user)
    except Account.DoesNotExist:
        logging.error(f'Account not found for user {request.user.uuid}')
        return JsonResponse(
            {'success': False, 'error': _('There was an error retrieving your mail account.')},
            status=404,
        )

    # Get the local Email object
    aliases: list[Email] = Email.objects.filter(type=Email.EmailType.ALIAS, account=account).all()
    for alias in aliases:
        if alias.address.endswith(f'@{domain_name}'):
            return JsonResponse(
                {
                    'success': False,
                    'error': 'You must remove all aliases using this domain before you can remove the domain.',
                },
                status=400,
            )

    stalwart_client = MailClient()
    cleanup_phase = 'load_local_domains'
    try:
        domains = request.user.domains.filter(name__iexact=domain_name).all()
        # There should only be one here, but just in case...
        for _domain in domains:
            if _domain.stalwart_id:
                try:
                    cleanup_phase = 'delete_stalwart_domain'
                    stalwart_client.delete_domain(_domain.name)
                except DomainNotFoundError as ex:
                    # While it's not in Stalwart we seem to have a local reference,
                    # so try deleting dkim and then local ref
                    _capture_domain_exception(ex, domain, phase='delete_stalwart_domain_not_found')

            cleanup_phase = 'delete_dkim'
            stalwart_client.delete_dkim(_domain.name)

            cleanup_phase = 'delete_hosted_dkim_dns_records'
            mail_tasks.delete_hosted_dkim_dns_records.delay(_domain.name)
            break

        cleanup_phase = 'delete_local_domain'
        domain.delete()

    except Exception as e:
        logging.error(f'Error removing custom domain: {e}')
        _capture_domain_exception(e, domain, phase=cleanup_phase)
        return JsonResponse(
            {'success': False, 'error': 'An error occurred while removing the custom domain. Please try again later.'},
            status=500,
        )

    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def add_email_alias(request: HttpRequest):
    """Adds an email alias"""
    data = json.loads(request.body)
    email_alias = data.get('email-alias')
    domain = data.get('domain')
    is_shared_domain = domain in settings.ALLOWED_EMAIL_DOMAINS
    is_custom_domain = (
        domain in request.user.domains.values_list('name', flat=True) and not is_shared_domain
    )
    is_catch_all = is_custom_domain and (email_alias == '*' or email_alias == '')

    # We don't need to specify the asterisk for catch-all on stalwart's end.
    if is_catch_all:
        email_alias = ''

    email_alias = email_alias.lower()

    full_email_alias = f'{email_alias}@{domain}'

    if not is_catch_all and email_alias and '+' in email_alias:
        return JsonResponse(
            {'success': False, 'error': _('The + symbol is not allowed.')},
            status=400,
        )

    if domain in settings.ALLOWED_EMAIL_DOMAINS and len(email_alias) < settings.MIN_CUSTOM_DOMAIN_ALIAS_LENGTH:
        return JsonResponse(
            {'success': False, 'error': _('Email alias must be at least 3 characters long.')},
            status=400,
        )

    if not is_catch_all:
        # min_length=1 because the domain-specific minimum has already been checked above.
        try:
            validate_email(full_email_alias, min_length=1)
        except EmailNotValidError as ex:
            return JsonResponse({'success': False, 'error': ex.error_message}, status=400)

    if (not is_catch_all and not email_alias) or not domain:
        return JsonResponse({'success': False, 'error': _('Email alias and domain are required.')}, status=400)

    if (not is_catch_all and not is_custom_domain and is_reserved(email_alias)) or is_address_taken(full_email_alias):
        return JsonResponse({'success': False, 'error': _('You cannot use this email address.')}, status=403)

    if (
        domain not in request.user.domains.values_list('name', flat=True)
        and domain not in settings.ALLOWED_EMAIL_DOMAINS
    ):
        return JsonResponse({'success': False, 'error': _('Domain not found.')}, status=404)

    # Get the user's account
    try:
        account = Account.objects.get(user=request.user)
    except Account.DoesNotExist:
        logging.error(f'Account not found for user {request.user.uuid}')
        return JsonResponse(
            {'success': False, 'error': _('There was an error retrieving your mail account.')},
            status=404,
        )

    emails = account.email_set.filter(type=Email.EmailType.ALIAS.value).all()
    shared_domain_aliases = list(
        filter(None, [email.address.split('@')[1] in settings.ALLOWED_EMAIL_DOMAINS for email in emails])
    )

    # If it's a shared domain, add one to the count and see if we go over the plan's limit.
    if is_shared_domain and len(shared_domain_aliases) + 1 > request.user.plan.mail_address_count:
        return JsonResponse(
            {'success': False, 'error': _('You cannot create anymore aliases.')},
            status=400,
        )

    # Create the email alias record locally
    try:
        email_obj, created = Email.objects.get_or_create(
            address=full_email_alias,
            defaults={
                'type': Email.EmailType.ALIAS.value,
                'account': account,
            },
        )

        if not created:
            return JsonResponse(
                {'success': False, 'error': _('This email address is not available.')},
                status=400,
            )
    except Exception as e:
        logging.error(f'Error creating email alias: {e}')
        return JsonResponse(
            {'success': False, 'error': _('An error occurred while creating the email alias. Please try again later.')},
            status=500,
        )

    # Create the email alias in Stalwart
    try:
        stalwart_client = MailClient()
        stalwart_client.save_email_addresses(request.user.stalwart_primary_email, full_email_alias)
    except Exception as e:
        # If Stalwart creation fails, delete the local Email object
        email_obj.delete()

        logging.error(f'Error adding email alias: {e}')
        return JsonResponse(
            {'success': False, 'error': _('An error occurred while adding the email alias. Please try again later.')},
            status=500,
        )

    return JsonResponse({'success': True})


@login_required
@require_http_methods(['DELETE'])
def remove_email_alias(request: HttpRequest):
    """Removes an email alias"""
    data = json.loads(request.body)
    email_alias = data.get('email-alias')

    if not email_alias:
        return JsonResponse({'success': False, 'error': _('Email alias is required.')}, status=400)

    email_alias = email_alias.lower()

    # Get the account
    try:
        account = Account.objects.get(user=request.user)
    except Account.DoesNotExist:
        logging.error(f'Account not found for user {request.user.uuid}')
        return JsonResponse(
            {'success': False, 'error': _('There was an error retrieving your mail account to update.')},
            status=404,
        )

    # Get the local Email object
    try:
        email_obj = Email.objects.get(address__iexact=email_alias, type=Email.EmailType.ALIAS, account=account)
    except Email.DoesNotExist:
        logging.error(f'Email alias not found for user {request.user.uuid} and email {email_alias}')
        return JsonResponse(
            {'success': False, 'error': _('Email alias not found.')},
            status=404,
        )

    # Remove from Stalwart
    try:
        stalwart_client = MailClient()
        stalwart_client.delete_email_addresses(request.user.stalwart_primary_email, email_alias)
    except Exception as e:
        logging.error(f'Error removing email alias: {e}')
        return JsonResponse(
            {'success': False, 'error': _('An error occurred while removing the email alias. Please try again later.')},
            status=500,
        )

    # Remove the local Email object
    try:
        email_obj.delete()
    except Exception as e:
        # Don't return an error since Stalwart deletion succeeded
        # Just log the error for investigation
        logging.error(f'Error deleting email alias record: {e}')

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(['POST'])
def appointment_caldav_setup(request: HttpRequest):
    """Auto-setup for CalDAV for Appointment.
    This is meant to be called by Appointment's backend only.
    Receives an OIDC token, retrieves the user's Stalwart account
    and creates or retrieves a special App Password to be used in Appointment's CalDAV auto-setup"""

    error_response = JsonResponse(
        {'success': False, 'error': _('An error has occurred while setting up the Appointment CalDAV.')},
        status=400,
    )

    if not settings.APPOINTMENT_CALDAV_SECRET:
        logging.error('Appointment CalDAV secret is not set')
        error_response.status_code = 500
        return error_response

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logging.error('Invalid JSON body during Appointment CalDAV setup')
        error_response.status_code = 400
        return error_response

    appointment_secret = data.get('appointment-secret')

    # This endpoint is only meant to be called by Appointment's backend
    # so we need to verify a shared secret between them before proceeding
    if not appointment_secret or appointment_secret != settings.APPOINTMENT_CALDAV_SECRET:
        logging.error('Invalid appointment secret during Appointment CalDAV setup')
        return error_response

    access_token = data.get('oidc-access-token')

    if not access_token:
        logging.warning('OIDC access token is missing during Appointment CalDAV setup')
        return error_response

    # Validate the access token against the OIDC provider to identify the user
    try:
        oidc_backend = AccountsOIDCBackend(None)
        user = oidc_backend.get_user_from_access_token(access_token)
    except Exception as ex:
        sentry_sdk.capture_exception(ex)
        error_response.status_code = 401
        return error_response

    if not user:
        logging.error('User not found for access token during Appointment CalDAV setup')
        error_response.status_code = 404
        return error_response

    if not user.has_active_subscription:
        logging.error('User does not have an active subscription during Appointment CalDAV setup')
        error_response.status_code = 400
        return error_response

    # Use a special label for the App Password to be used in Appointment's CalDAV auto-setup
    label = f'{settings.APPOINTMENT_APP_PASSWORD_PREFIX}{user.stalwart_primary_email}'

    try:
        stalwart_client = MailClient()
        email_user = stalwart_client.get_account(user.stalwart_primary_email)

        # Remove any existing app password for this label so we can
        # replace it with a fresh one.
        expected_prefix = f'$app${label}$'
        for secret in email_user.get('secrets', []):
            if secret.startswith(expected_prefix):
                stalwart_client.delete_app_password(user.stalwart_primary_email, secret)

        # Generate a random base64 password, hash it for Stalwart
        # storage, and return the base64 password to the caller for CalDAV auth.
        base64_password = secrets.token_urlsafe(64)
        app_password_hash = utils.save_app_password(label, base64_password)
        stalwart_client.save_app_password(user.stalwart_primary_email, app_password_hash)

        return JsonResponse({'success': True, 'app_password': base64_password})

    except Exception as ex:
        sentry_sdk.capture_exception(ex)
        error_response.status_code = 500
        return error_response


@login_required
def jmap_test_page(request: HttpRequest):
    from thunderbird_accounts.mail.tiny_jmap_client import TinyJMAPClient

    """A test script that should not be ran in non-dev environments.
    This is based off the jmap spec sample code:
    https://github.com/fastmail/JMAP-Samples/blob/main/python3/top-ten.py"""
    user = request.user
    access_token = request.session['oidc_access_token']
    inboxes = []

    try:
        if not access_token:
            raise AccessTokenNotFound('Access token is not in session object. User may need to re-login.')

        client = TinyJMAPClient(
            hostname=settings.STALWART_BASE_JMAP_URL,
            username=user.username,
            token=access_token,
        )
        account_id = client.get_account_id()

        inbox_res = client.make_jmap_call(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
                'methodCalls': [
                    [
                        'Mailbox/query',
                        {
                            'accountId': account_id,
                            'filter': {'role': 'inbox', 'hasAnyRole': True},
                        },
                        'a',
                    ]
                ],
            }
        )
        inboxes = inbox_res['methodResponses'][0][1]['ids']
    except (AccessTokenNotFound, requests.exceptions.HTTPError, Exception) as ex:
        logging.error('Jmap test route failed')
        logging.exception(ex)

    return JsonResponse(
        {
            'jmap_url': f'{settings.STALWART_BASE_JMAP_URL}/.well-known/jmap',
            'username': user.username,
            'connection': len(inboxes) > 0,
        }
    )


@method_decorator(never_cache, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class AdminStalwartList(TemplateView):
    template_name = 'admin_stalwart_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        stalwart = MailClient()
        response = stalwart._list_principals()
        data = response.json().get('data', {}).get('items', [])

        context.update(
            {
                'app_label': 'mail',
                'items': [
                    {
                        'id': principal.get('id'),
                        'name': principal.get('name'),
                        'type': principal.get('type'),
                        'description': principal.get('description'),
                        'emails': principal.get('emails'),
                        'roles': principal.get('roles'),
                        'members': principal.get('members'),
                        'quota': principal.get('quota'),
                        'quota_used': principal.get('usedQuota'),
                    }
                    for principal in data
                ],
            }
        )

        return context

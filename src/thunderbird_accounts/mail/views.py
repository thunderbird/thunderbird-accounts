import datetime
import json
import logging

import requests.exceptions
import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.signing import Signer
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.contrib.messages import get_messages

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.reserved import is_reserved
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import AccessTokenNotFound, AccountNotFoundError, DomainAlreadyExistsError
from thunderbird_accounts.mail.utils import decode_app_password

try:
    from paddle_billing import Client
    from paddle_billing.Resources.CustomerPortalSessions.Operations import CreateCustomerPortalSession
except ImportError:
    Client = None
    CreateCustomerPortalSession = None

from thunderbird_accounts.mail.models import Account, Email, Domain
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Plan, Price
from thunderbird_accounts.mail.zendesk import ZendeskClient
from thunderbird_accounts.mail import utils


def raise_form_error(request, to_view: str, error_message: str):
    """Puts the error message into the message bag and redirects to a named view."""
    messages.error(request, error_message, extra_tags='form-error')
    return HttpResponseRedirect(to_view)


def home(request: HttpRequest):
    app_passwords = []
    user_display_name = None
    custom_domains = []
    email_addresses = []
    max_custom_domains = None
    max_email_aliases = None

    if request.user.is_authenticated and request.user.has_active_subscription:
        try:
            account = request.user.account_set.first()
            if not account:
                raise AccountNotFoundError(username=request.user.stalwart_primary_email)

            stalwart_client = MailClient()

            email_user = stalwart_client.get_account(request.user.stalwart_primary_email)
            user_display_name = email_user.get('description')

            # Get user's app password from Stalwart
            for secret in email_user.get('secrets', []):
                app_passwords.append(decode_app_password(secret))

            # Get user's email addresses from Stalwart
            email_addresses = email_user.get('emails', [])
        except AccountNotFoundError:
            app_passwords = []
            messages.error(request, _('Could not connect to Thundermail, please try again later.'))
        except requests.ConnectionError as ex:
            sentry_sdk.capture_exception(ex)
            messages.error(
                request,
                _('Thundermail is experiencing some connection issues, some aspects of the site may be unavailable.'),
            )

        # Get user's custom domains
        domains = request.user.domains.all()
        custom_domains = [
            {
                'name': domain.name,
                'status': domain.status,
            }
            for domain in domains
        ]

        # Get user's plan info constraints
        if request.user.plan:
            max_custom_domains = request.user.plan.mail_domain_count
            max_email_aliases = request.user.plan.mail_address_count
    elif not request.user.is_authenticated:  # Only if the user is not authenticated
        # Check if path is included in Vue's public routes (assets/app/vue/router.ts)
        public_routes = ['/privacy', '/terms']

        if request.path not in public_routes:
            return HttpResponseRedirect(reverse('login'))

    return TemplateResponse(
        request,
        'mail/index.html',
        {
            'connection_info': settings.CONNECTION_INFO,
            'app_passwords': json.dumps(app_passwords),
            'user_display_name': user_display_name,
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS,
            'custom_domains': json.dumps(custom_domains),
            'email_addresses': json.dumps(email_addresses),
            'max_custom_domains': max_custom_domains,
            'max_email_aliases': max_email_aliases,
            'tb_pro_appointment_url': settings.TB_PRO_APPOINTMENT_URL,
            'tb_pro_send_url': settings.TB_PRO_SEND_URL,
            'server_messages': [
                {'level': message.level, 'message': str(message.message) } for message in get_messages(request)
            ],
        },
    )


@login_required
def sign_up(request: HttpRequest):
    # If we're posting ourselves, we're logging in
    if request.method == 'POST':
        return HttpResponseRedirect(reverse('self-serve'))

    return TemplateResponse(
        request,
        'mail/sign-up/index.html',
        {
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS,
            'cancel_redirect': reverse('self_serve_account_info'),
        },
    )


@require_http_methods(['POST'])
def sign_up_submit(request: HttpRequest):
    if request.user.is_anonymous:
        return HttpResponseRedirect('/')
    if len(request.user.account_set.all()) > 0:
        return raise_form_error(request, reverse('sign_up'), _('You already have an account'))
    if not request.POST['app_password'] or not request.POST['email_address'] or not request.POST['email_domain']:
        return raise_form_error(request, reverse('sign_up'), _('Required fields are not set'))
    if request.POST['email_domain'] not in settings.ALLOWED_EMAIL_DOMAINS:
        return raise_form_error(request, reverse('sign_up'), _('Invalid domain selected'))

    email_address = request.POST['email_address'].strip()
    email_address = f'{email_address}@{request.POST["email_domain"]}'

    try:
        Email.objects.get(address=email_address)
        return raise_form_error(request, reverse('sign_up'), _('Requested email is already taken'))
    except Email.DoesNotExist:
        pass

    user = request.user

    # Set the user's username to the new primary email address and save the user
    user.username = email_address
    user.save()

    app_password = request.POST['app_password']

    # Send a task to create the inbox / account on stalwart's end
    if app_password:
        # Form the encrypted app password
        app_password = utils.save_app_password('Mail Client', app_password)

    success = utils.create_stalwart_account(user, app_password)

    if success:
        return HttpResponseRedirect(reverse('self_serve_connection_info'))

    return HttpResponseRedirect(reverse('sign_up'))


def self_serve_common_options(is_account_settings: bool, user: User, account: Account):
    """Common return params for self serve pages"""
    return {
        'has_account': True if account else False,
        'is_account_settings': is_account_settings,
        'has_active_subscription': user.has_active_subscription,
    }


def contact(request: HttpRequest):
    """Contact page for support requests (uses ZenDesk's API)
    A user can always access this page even if they don't have a mail account setup
    since they might encounter problems before the mail account setup itself."""
    return TemplateResponse(request, 'mail/contact.html')


@require_http_methods(['GET'])
def contact_fields(request: HttpRequest):
    """Get ticket fields from Zendesk API and filter for fields with custom options."""
    zendesk_client = ZendeskClient()
    result = zendesk_client.get_ticket_fields()

    if not result['success']:
        return JsonResponse(
            {'success': False, 'error': result.get('error', _('Failed to fetch ticket fields'))}, status=500
        )

    ticket_fields = result['data']['ticket_fields']
    fields_by_title = {}

    # Filter ticket fields to only include those with custom_field_options
    for field in ticket_fields:
        if 'custom_field_options' in field:
            # Extract the id, title, and custom_field_options with id, name and value
            field_data = {
                'id': field['id'],
                'title': field['title'],
                'custom_field_options': [
                    {'id': option['id'], 'name': option['name'], 'value': option['value']}
                    for option in field['custom_field_options']
                ],
            }
            fields_by_title[field['title']] = field_data

    return JsonResponse({'success': True, 'ticket_fields': fields_by_title})


@require_http_methods(['POST'])
def contact_submit(request: HttpRequest):
    """Uses Zendesk's Requests API to create a ticket
    Ref https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#tickets-and-requests"""

    email = request.POST.get('email')
    subject = request.POST.get('subject')
    product = request.POST.get('product')
    product_field_id = request.POST.get('product_field_id')
    ticket_type = request.POST.get('type')
    type_field_id = request.POST.get('type_field_id')
    description = request.POST.get('description')
    uploaded_files = request.FILES.getlist('attachments')

    if not any([email, subject, product, ticket_type, description]):
        return raise_form_error(request, reverse('contact'), _('All fields are required'))

    # Upload files to Zendesk and collect tokens
    attachment_tokens = []
    zendesk_client = ZendeskClient()

    for uploaded_file in uploaded_files:
        try:
            zendesk_api_response = zendesk_client.upload_file(uploaded_file)

            if not zendesk_api_response['success']:
                return JsonResponse(
                    {
                        'success': False,
                        'error': _('Failed to upload file {uploaded_file_name}: {zendesk_api_response_error}').format(
                            uploaded_file_name=uploaded_file.name,
                            zendesk_api_response_error=zendesk_api_response.get('error', _('Unknown error')),
                        ),
                    },
                    status=500,
                )

            attachment_tokens.append(
                {'token': zendesk_api_response['upload_token'], 'filename': zendesk_api_response['filename']}
            )

        except Exception as e:
            return JsonResponse(
                {
                    'success': False,
                    'error': _('Failed to upload file {uploaded_file_name}: {error}').format(
                        uploaded_file_name=uploaded_file.name, error=str(e)
                    ),
                },
                status=500,
            )

    # Create ticket with attachment tokens
    ticket_fields = {
        'email': email,
        'subject': subject,
        'product': product,
        'product_field_id': product_field_id,
        'ticket_type': ticket_type,
        'type_field_id': type_field_id,
        'description': description,
        'attachments': attachment_tokens,
    }

    zendesk_api_response = zendesk_client.create_ticket(ticket_fields)

    if zendesk_api_response.ok:
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=500)


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def app_password_set(request: HttpRequest):
    """Sets an app password for a remote Stalwart account"""

    try:
        data = json.loads(request.body)
        new_password = data.get('password')
        label = data.get('name')

        if not new_password or not label:
            return JsonResponse({
                'success': False,
                'error': str(_('Label and password are required'))
            }, status=400)

        stalwart_client = MailClient()

        email_user = stalwart_client.get_account(request.user.stalwart_primary_email)

        # Find and delete all previously existing app passwords
        for secret in email_user.get('secrets', []):
            stalwart_client.delete_app_password(request.user.stalwart_primary_email, secret)

        # Create and save the new app password
        new_secret = utils.save_app_password(label, new_password)
        stalwart_client.save_app_password(request.user.stalwart_primary_email, new_secret)

        return JsonResponse({
            'success': True,
            'message': str(_('Password set successfully'))
        })

    except AccountNotFoundError:
        return JsonResponse({
            'success': False,
            'error': str(_('Could not connect to Thundermail, please try again later.'))
        }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': str(_('Invalid request data'))
        }, status=400)
    except Exception as e:
        logging.error(f'Error setting app password: {e}')
        return JsonResponse({
            'success': False,
            'error': str(_('An error occurred while setting the password. Please try again.'))
        }, status=500)


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('display-name')
def display_name_set(request: HttpRequest):
    """Sets a display name for a remote Stalwart account"""

    try:
        data = json.loads(request.body)
        display_name = data.get('display-name')
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': str(_('Invalid request data'))
        }, status=400)

    if not display_name:
        return JsonResponse({
            'success': False,
            'error': str(_('Display name is required'))
        }, status=400)

    stalwart_client = MailClient()
    try:
        stalwart_client.update_individual(request.user.stalwart_primary_email, full_name=display_name)
    except AccountNotFoundError:
        messages.error(request, _('Could not connect to Thundermail, please try again later.'))

    return JsonResponse({
        'success': True,
        'message': str(_('Display name set successfully'))
    })


@login_required
@require_http_methods(['POST'])
def create_custom_domain(request: HttpRequest):
    """Creates a custom domain for the user"""
    data = json.loads(request.body)
    domain_name = data.get('domain-name')

    if not domain_name:
        return JsonResponse({'success': False, 'error': _('Domain name is required')}, status=400)

    custom_domain_count = request.user.domains.count()

    if custom_domain_count >= request.user.plan.mail_domain_count:
        return JsonResponse(
            {'success': False, 'error': _('You have reached the maximum number of custom domains')}, status=400
        )

    try:
        stalwart_client = MailClient()

        domain_id = stalwart_client.create_domain(domain_name)
        stalwart_client.create_dkim(domain_name)

        now = datetime.datetime.now(datetime.UTC)
        Domain.objects.create(name=domain_name, user=request.user, stalwart_id=domain_id, stalwart_created_at=now)
    except DomainAlreadyExistsError:
        return JsonResponse({'success': False, 'error': _('Domain already exists')}, status=400)
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
        dns_records = stalwart_client.get_dns_records(domain.name)
        return JsonResponse({'success': True, 'dns_records': dns_records})
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

    domain = request.user.domains.get(name=domain_name)
    if not domain:
        return JsonResponse({'success': False, 'error': _('Domain not found')}, status=404)

    stalwart_client = MailClient()

    now = datetime.datetime.now(datetime.UTC)

    try:
        # For dev / localhost we can't verify domains, so we will always return success
        if settings.IS_DEV:
            domain.status = Domain.DomainStatus.VERIFIED
            domain.verified_at = now
            domain.save()
            return JsonResponse({'success': True, 'critical_errors': [], 'warnings': []})

        is_verified, critical_errors, warnings = stalwart_client.verify_domain(domain.name)

        domain.last_verification_attempt = now

        if is_verified:
            domain.status = Domain.DomainStatus.VERIFIED
            domain.verified_at = now
            domain.save()

            return JsonResponse({
                'success': True,
                'critical_errors': critical_errors,
                'warnings': warnings
            })
        else:
            domain.status = Domain.DomainStatus.FAILED
            domain.save()

            return JsonResponse({
                'success': False,
                'critical_errors': critical_errors,
                'warnings': warnings
            })
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

    domain = request.user.domains.get(name=domain_name)
    if not domain:
        return JsonResponse({'success': False, 'error': _('Domain not found')}, status=404)

    stalwart_client = MailClient()
    try:
        stalwart_client.delete_domain(domain.name)
        request.user.domains.filter(name=domain_name).delete()
    except Exception as e:
        logging.error(f'Error removing custom domain: {e}')
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

    if not email_alias or not domain:
        return JsonResponse({'success': False, 'error': _('Email alias and domain are required.')}, status=400)

    if is_reserved(email_alias):
        return JsonResponse({'success': False, 'error': _('You cannot use this email address.')}, status=403)

    if (
        domain not in request.user.domains.values_list('name', flat=True)
        and domain not in settings.ALLOWED_EMAIL_DOMAINS
    ):
        return JsonResponse({'success': False, 'error': _('Domain not found.')}, status=404)

    full_email_alias = f'{email_alias}@{domain}'

    # Get the user's account
    try:
        account = Account.objects.get(user=request.user)
    except Account.DoesNotExist:
        logging.error(f'Account not found for user {request.user.uuid}')
        return JsonResponse(
            {'success': False, 'error': _('There was an error retrieving your mail account.')},
            status=404,
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
        email_obj = Email.objects.get(address=email_alias, type=Email.EmailType.ALIAS, account=account)
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


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {'form_action': settings.WAIT_LIST_FORM_ACTION})


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


@require_http_methods(['POST'])
@staff_member_required()
def purge_stalwart_accounts(request: HttpRequest):
    """
    Allows up to clean up the test data before the proper oidc schema has been finallized.
    """
    stalwart = MailClient()

    # Grab list of individuals
    response = stalwart._list_principals(type='individual')
    data = response.json().get('data', {}).get('items', [])

    # Loop through and delete them
    for account in data:
        stalwart._delete_principal(account.get('name'))

    # Grab a fresh list of all principals to confirm
    response = stalwart._list_principals()
    rest_of_data = response.json().get('data', {}).get('items', [])
    return JsonResponse({'deleted_individuals': data, 'not_deleted_data': rest_of_data})


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

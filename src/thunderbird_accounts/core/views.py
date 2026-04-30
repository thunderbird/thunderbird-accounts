from thunderbird_accounts.core.utils import get_feature_flags
from thunderbird_accounts.authentication.exceptions import AuthenticationUnavailable
from gettext import gettext
import sys
import json
import requests

import requests.exceptions
import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from django.contrib.messages import get_messages

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
)
from thunderbird_accounts.mail.utils import decode_app_password, filter_app_passwords

from thunderbird_accounts.core.zendesk import ZendeskClient
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse


def handle_500(request: HttpRequest, template_name=None):
    """Overrides Django's default 500 error page with our own"""
    # Retrieve the last known exception
    last_exception = sys.exc_info()[1]

    error_title = gettext('Unknown Error')
    if last_exception and isinstance(last_exception, AuthenticationUnavailable):
        error_title = gettext('Thunderbird Accounts is currently unavailable')

    # We ignore template_name and use our own here.
    return TemplateResponse(
        request,
        'errors/tbpro_500.html',
        {
            'error_title': error_title,
        },
        status=500,
    )


def home(request: HttpRequest):
    """The main route for our VueJS app.
    This prepares some data for the initial form load (like authentication information, plan information, and the like.)
    """
    app_passwords = []
    user_display_name = None
    custom_domains = []
    email_addresses = []
    max_custom_domains = None
    max_email_aliases = None
    needs_tos_acceptance = False

    # This state can only really happen when a user hits PermissionDenied immediately upon logging in.
    # They will be logged in via Keycloak and then a redirect loop will happen as we deny them permission,
    # redirect them to login. Since the store_token function occurs before the permission check, we can
    # use these conditions to ship the user to logout and thus "fixing" the redirect loop.
    if request.session.get('oidc_access_token') and not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('logout'))

    if request.user.is_authenticated and request.user.has_active_subscription:
        try:
            account = request.user.account_set.first()
            if not account:
                raise AccountNotFoundError(username=request.user.stalwart_primary_email)

            stalwart_client = MailClient()

            email_user = stalwart_client.get_account(request.user.stalwart_primary_email)
            user_display_name = email_user.get('description')

            # Get user's app passwords from Stalwart, excluding internal ones
            for secret in filter_app_passwords(email_user.get('secrets', [])):
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
        public_routes = ['/privacy', '/terms', '/contact', '/sign-up', '/sign-up/complete', '/logout', '/error']

        if request.path not in public_routes:
            return HttpResponseRedirect(reverse('login'))

    # Check if the user needs to accept the latest legal documents
    if request.user.is_authenticated:
        legal_doc_count = LegalDocument.objects.filter(is_current=True).count()
        accepted_current_doc_count = LegalDocument.objects.filter(
            is_current=True,
            responses__user=request.user,
            responses__action=LegalDocumentResponse.Action.ACCEPTED,
        ).distinct().count()
        needs_tos_acceptance = legal_doc_count != accepted_current_doc_count

    form_data = request.session.get('form_data')
    if request.session.get('form_data'):
        # Clear form_data for any additional reloads
        request.session['form_data'] = {}

    return TemplateResponse(
        request,
        'index.html',
        {
            'connection_info': settings.CONNECTION_INFO,
            'app_passwords': json.dumps(app_passwords),
            'user_display_name': user_display_name,
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS if settings.ALLOWED_EMAIL_DOMAINS else [],
            'custom_domains': json.dumps(custom_domains),
            'email_addresses': json.dumps(email_addresses),
            'max_custom_domains': max_custom_domains,
            'max_email_aliases': max_email_aliases,
            'tb_pro_appointment_url': settings.TB_PRO_APPOINTMENT_URL,
            'tb_pro_send_url': settings.TB_PRO_SEND_URL,
            'tb_pro_primary_domain': settings.PRIMARY_EMAIL_DOMAIN,
            'server_messages': [
                {'level': message.level, 'message': str(message.message)} for message in get_messages(request)
            ],
            'form_data': form_data or None,
            'features': json.dumps(get_feature_flags()),
            'needs_tos_acceptance': needs_tos_acceptance,
        },
    )


@require_http_methods(['GET'])
@cache_page(60 * 15)
def contact_fields(request: HttpRequest):
    """Get ticket fields from Zendesk API and filter based on Zendesk Admin."""
    zendesk_client = ZendeskClient()
    result = zendesk_client.get_ticket_fields()

    if not result['success']:
        return JsonResponse(
            {'success': False, 'error': result.get('error', _('Failed to fetch ticket fields'))}, status=500
        )

    ticket_form = result['data']['ticket_form']
    ticket_fields = result['data']['ticket_fields']

    # For now, we only care about the id of the ticket form, since we need to pass it back to ticket creation
    # Even though we could read this from the env var ZENDESK_FORM_ID directly, we might need more fields in the future
    ticket_form_data = {'id': ticket_form['id']}

    ticket_fields_data = []

    # Filter ticket fields based on being editable / visible (controlled through Zendesk Admin)
    for field in ticket_fields:
        if field.get('active') and field.get('visible_in_portal') and field.get('editable_in_portal'):
            field_data = {
                'id': field.get('id'),
                'title': field.get('title_in_portal') or field.get('title', ''),
                'description': field.get('description', ''),
                'required': field.get('required_in_portal') or field.get('required', False),
                'type': field.get('type', ''),
            }

            if 'custom_field_options' in field:
                # Extract the id, name, and custom_field_options with id, name and value
                field_data['custom_field_options'] = [
                    {'id': option.get('id'), 'name': option.get('name', ''), 'value': option.get('value', '')}
                    for option in field['custom_field_options']
                ]

            ticket_fields_data.append(field_data)

    return JsonResponse({'success': True, 'ticket_form': ticket_form_data, 'ticket_fields': ticket_fields_data})


@require_http_methods(['POST'])
def contact_submit(request: HttpRequest):
    """Uses Zendesk's Requests API to create a ticket
    Ref https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#tickets-and-requests"""

    # Data comes in as multipart/form-data, so we need to parse the JSON data from the form
    # using the 'data' field so that we can also send attachments in the same request
    try:
        data_json = json.loads(request.POST.get('data', '{}'))
    except json.JSONDecodeError as ex:
        sentry_sdk.capture_exception(ex)
        return JsonResponse({'success': False, 'error': _('Invalid form data')}, status=400)

    email = data_json.get('email')

    # Name is optional in the UI,
    # but it is required for the Zendesk Requests API's requester object
    # So we default to the email address if the name is not provided
    name = data_json.get('name', email)

    fields = data_json.get('fields', [])

    # Extract subject and description from dynamic fields.
    # Even though they come in as dynamic fields, they are special mandatory fields
    # that should be sent differently in the Request API.
    # https://developer.zendesk.com/api-reference/ticketing/tickets/ticket-requests/#json-format
    subject = None
    description = None

    custom_fields = []
    validation_errors = []

    for field in fields:
        field_type = field.get('type')
        field_value = field.get('value')
        field_id = field.get('id')
        field_title = field.get('title')
        field_required = field.get('required', False)

        # Check if required field is empty
        if field_required and (not field_value or field_value.strip() == ''):
            validation_errors.append(f'{field_title} is required')

        if field_type == 'subject':
            subject = field_value
        elif field_type == 'description':
            description = field_value
        else:
            # This is a custom field
            custom_fields.append({'id': field_id, 'value': field_value})

    uploaded_files = request.FILES.getlist('attachments')

    # Check for validation errors
    if validation_errors:
        return JsonResponse({'success': False, 'error': ', '.join(validation_errors)}, status=400)

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

        except Exception as ex:
            sentry_sdk.capture_exception(ex)
            return JsonResponse(
                {
                    'success': False,
                    'error': _('Failed to upload file {uploaded_file_name}. Please try again later.').format(
                        uploaded_file_name=uploaded_file.name
                    ),
                },
                status=500,
            )

    # Create ticket with attachment tokens
    ticket_fields = {
        'ticket_form_id': int(settings.ZENDESK_FORM_ID),
        'name': name,
        'email': email,
        'subject': subject,
        'description': description,
        'attachments': attachment_tokens,
        'custom_fields': custom_fields,
    }

    zendesk_api_response = zendesk_client.create_ticket(ticket_fields)

    if not zendesk_api_response.ok:
        sentry_sdk.capture_message(
            f'Failed to create Zendesk ticket: {zendesk_api_response}',
            level='error',
        )
        return JsonResponse({'success': False}, status=500)

    # Extract the ticket ID from the response
    response_data = zendesk_api_response.json()
    ticket_id = response_data['request']['id']

    # Add browser and OS information to hidden custom fields
    from thunderbird_accounts.core.utils import parse_user_agent_info

    user_agent_string = request.headers.get('User-Agent')
    browser_string, os_string = parse_user_agent_info(user_agent_string)

    # Hidden fields (e.g. fields with permissions set as 'Agents can edit')
    # can't be submitted through the Requests API, so we need to update the ticket manually
    # using the Tickets API instead on behalf of the agent (not the end user)
    update_ticket_fields = {
        'custom_fields': [
            {'id': int(settings.ZENDESK_FORM_BROWSER_FIELD_ID), 'value': browser_string},
            {'id': int(settings.ZENDESK_FORM_OS_FIELD_ID), 'value': os_string},
        ]
    }

    zendesk_api_response = zendesk_client.update_ticket(ticket_id, update_ticket_fields)

    if not zendesk_api_response.ok:
        # At this point the ticket has been created, even though we couldn't update the hidden fields
        # So we should capture the error but still return success to the user
        sentry_sdk.capture_message(
            f'Zendesk ticket created but failed to update hidden fields: {zendesk_api_response}',
            level='error',
            user={'ticket_id': ticket_id},
        )

    return JsonResponse({'success': True})

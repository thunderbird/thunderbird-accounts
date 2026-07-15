from requests import JSONDecodeError
import json

import sentry_sdk
from django.conf import settings
from django.core.validators import EMPTY_VALUES
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from thunderbird_accounts.support.zendesk import ZendeskClient

# Add browser and OS information to hidden custom fields
from thunderbird_accounts.core.utils import parse_user_agent_info


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
    # So we default to the email address if the name is missing or empty.
    name = data_json.get('name') or email

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

    # TODO: Refactor this view to use Django's Forms API instead of direct EMPTY_VALUES access.
    if email in EMPTY_VALUES:
        validation_errors.append('Email is required')

    if subject in EMPTY_VALUES:
        validation_errors.append('Subject is required')

    if description in EMPTY_VALUES:
        validation_errors.append('Description is required')

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
    try:
        response_data = zendesk_api_response.json()
        ticket_id = response_data['request']['id']
    except (KeyError, JSONDecodeError) as ex:
        sentry_sdk.set_context('exception_data', {
            'ex': ex,
            'zendesk_api_response': zendesk_api_response,
            'response_data': response_data,
        })
        sentry_sdk.capture_message(
            f'Failed to create Zendesk ticket: {zendesk_api_response}',
            level='error',
        )
        return JsonResponse({'success': False}, status=500)


    user_agent_string = request.headers.get('User-Agent')
    browser_string, os_string = parse_user_agent_info(user_agent_string or '')

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

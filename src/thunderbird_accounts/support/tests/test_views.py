import json
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as RequestClient, TestCase, override_settings
from django.urls import reverse

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.subscription.models import Subscription
from thunderbird_accounts.support.views import get_plan_status_for_zendesk

MANAGED_DOMAIN = 'thundermail.example'


class ZendeskContactFieldsTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_contact_fields_success_filters_and_transforms(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.get_ticket_fields.return_value = {
            'success': True,
            'data': {
                'ticket_form': {'id': 123, 'name': 'Support'},
                'ticket_fields': [
                    {
                        'id': 1,
                        'title': 'Subject',
                        'description': 'Subject field',
                        'required': True,
                        'type': 'subject',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': True,
                    },
                    {
                        'id': 2,
                        'title': 'Category',
                        'description': 'Choose a category',
                        'required': False,
                        'type': 'tagger',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': True,
                        'custom_field_options': [
                            {'id': 21, 'name': 'General', 'value': 'general', 'extra': 'ignored'},
                            {'id': 22, 'name': 'Billing', 'value': 'billing'},
                        ],
                    },
                    {
                        # Should be filtered out (not editable in portal)
                        'id': 3,
                        'title': 'Internal',
                        'description': 'Internal only',
                        'required': False,
                        'type': 'text',
                        'active': True,
                        'visible_in_portal': True,
                        'editable_in_portal': False,
                    },
                ],
            },
        }

        url = reverse('contact_fields')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())

        self.assertTrue(payload['success'])
        self.assertEqual(payload['ticket_form'], {'id': 123})
        self.assertIn('ticket_fields', payload)

        # Only two fields should pass the filter
        fields = payload['ticket_fields']
        self.assertEqual(len(fields), 2)

        # Field 1 minimal keys + values
        f1 = next(f for f in fields if f['id'] == 1)
        self.assertEqual(
            {k: f1[k] for k in ['id', 'title', 'description', 'required', 'type']},
            {'id': 1, 'title': 'Subject', 'description': 'Subject field', 'required': True, 'type': 'subject'},
        )
        self.assertNotIn('custom_field_options', f1)

        # Field 2 options trimmed to id/name/value
        f2 = next(f for f in fields if f['id'] == 2)
        self.assertEqual(f2['title'], 'Category')
        self.assertIn('custom_field_options', f2)
        self.assertEqual(
            f2['custom_field_options'],
            [
                {'id': 21, 'name': 'General', 'value': 'general'},
                {'id': 22, 'name': 'Billing', 'value': 'billing'},
            ],
        )

        # Ensure client was called once
        instance.get_ticket_fields.assert_called_once()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_contact_fields_error_from_backend(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.get_ticket_fields.return_value = {'success': False, 'error': 'Boom'}

        url = reverse('contact_fields')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload, {'success': False, 'error': 'Boom'})

    def test_contact_fields_method_not_allowed(self):
        url = reverse('contact_fields')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 405)


@override_settings(ALLOWED_EMAIL_DOMAINS=[MANAGED_DOMAIN], CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=False)
class ZendeskContactSubmitTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = RequestClient()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @patch('thunderbird_accounts.support.views.parse_user_agent_info')
    @override_settings(
        ZENDESK_FORM_ID='42',
        ZENDESK_FORM_BROWSER_FIELD_ID='1001',
        ZENDESK_FORM_OS_FIELD_ID='1002',
    )
    def test_contact_submit_success_with_attachments(self, mock_parse_ua, mock_client_cls):
        mock_parse_ua.return_value = ('Firefox 120', 'macOS 14')

        instance = Mock()
        mock_client_cls.return_value = instance
        instance.upload_file.return_value = {'success': True, 'upload_token': 'tok123', 'filename': 'test.txt'}

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = True
        instance.update_ticket.return_value = update_resp

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
                {'id': 13, 'title': 'Category', 'type': 'tagger', 'value': 'general', 'required': False},
            ],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(
            url,
            data={'data': json.dumps(payload), 'attachments': uploaded},
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {'success': True})

        # upload called for the file
        instance.upload_file.assert_called_once()
        # create called with expected payload
        args, _kwargs = instance.create_ticket.call_args
        sent_fields = args[0]
        self.assertEqual(sent_fields['ticket_form_id'], 42)
        self.assertEqual(sent_fields['name'], 'user@example.org')  # Defaults to email when name not provided
        self.assertEqual(sent_fields['email'], 'user@example.org')
        self.assertEqual(sent_fields['subject'], 'Hello')
        self.assertEqual(sent_fields['description'], 'Body')
        self.assertEqual(sent_fields['attachments'], [{'token': 'tok123', 'filename': 'test.txt'}])
        self.assertEqual(sent_fields['custom_fields'], [{'id': 13, 'value': 'general'}])

        # update called with browser/os hidden fields
        instance.update_ticket.assert_called_once()

        # Ensure the IDs are ints and values are what we mocked from UA
        update_payload = instance.update_ticket.call_args.args[1]
        self.assertEqual(
            update_payload,
            {
                'custom_fields': [
                    {'id': 1001, 'value': 'Firefox 120'},
                    {'id': 1002, 'value': 'macOS 14'},
                ]
            },
        )

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_contact_submit_validation_error_for_required_field(self, mock_client_cls):
        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': '', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        response = self.client.post(url, data={'data': json.dumps(payload)})
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content.decode())
        self.assertFalse(body['success'])
        self.assertIn('Subject is required', body['error'])
        # Ensure no calls were made to the client
        mock_client_cls.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_contact_submit_rejects_missing_required_zendesk_fields_before_upload(self, mock_client_cls):
        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'name': 'User',
            'fields': [],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(url, data={'data': json.dumps(payload), 'attachments': uploaded})

        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content.decode())
        self.assertFalse(body['success'])
        self.assertIn('Subject is required', body['error'])
        self.assertIn('Description is required', body['error'])
        mock_client_cls.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_contact_submit_rejects_missing_data_payload(self, mock_client_cls):
        url = reverse('contact_submit')
        response = self.client.post(url, data={})

        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content.decode())
        self.assertFalse(body['success'])
        self.assertIn('Email is required', body['error'])
        self.assertIn('Subject is required', body['error'])
        self.assertIn('Description is required', body['error'])
        mock_client_cls.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @override_settings(ZENDESK_FORM_ID='42')
    def test_contact_submit_upload_failure(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.upload_file.return_value = {'success': False, 'error': 'Zendesk upload failed'}

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(url, data={'data': json.dumps(payload), 'attachments': uploaded})

        self.assertEqual(response.status_code, 500)
        body = json.loads(response.content.decode())
        self.assertFalse(body['success'])
        self.assertIn('Failed to upload file test.txt:', body['error'])
        # create_ticket should not be called
        instance.create_ticket.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @override_settings(ZENDESK_FORM_ID='42')
    def test_contact_submit_upload_exception(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(url, data={'data': json.dumps(payload), 'attachments': uploaded})

        self.assertEqual(response.status_code, 500)
        body = json.loads(response.content.decode())
        self.assertFalse(body['success'])
        self.assertIn('Failed to upload file test.txt', body['error'])
        instance.create_ticket.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @override_settings(ZENDESK_FORM_ID='42')
    def test_contact_submit_create_ticket_failure(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.upload_file.return_value = {'success': True, 'upload_token': 'tok123', 'filename': 'test.txt'}
        create_resp = Mock()
        create_resp.ok = False
        instance.create_ticket.return_value = create_resp

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(url, data={'data': json.dumps(payload), 'attachments': uploaded})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.content.decode()), {'success': False})
        instance.update_ticket.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @patch('thunderbird_accounts.support.views.parse_user_agent_info')
    @override_settings(
        ZENDESK_FORM_ID='42',
        ZENDESK_FORM_BROWSER_FIELD_ID='1001',
        ZENDESK_FORM_OS_FIELD_ID='1002',
    )
    def test_contact_submit_update_ticket_failure(self, mock_parse_ua, mock_client_cls):
        mock_parse_ua.return_value = ('Firefox 120', 'macOS 14')

        instance = Mock()
        mock_client_cls.return_value = instance
        instance.upload_file.return_value = {'success': True, 'upload_token': 'tok123', 'filename': 'test.txt'}

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = False
        instance.update_ticket.return_value = update_resp

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')
        response = self.client.post(url, data={'data': json.dumps(payload), 'attachments': uploaded})

        # Even though the update failed, at this point the ticket was created successfully
        # So we were just unable to update the hidden fields, so we still return success to the user
        instance.update_ticket.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {'success': True})

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @patch('thunderbird_accounts.support.views.parse_user_agent_info')
    @override_settings(
        ZENDESK_FORM_ID='42',
        ZENDESK_FORM_BROWSER_FIELD_ID='1001',
        ZENDESK_FORM_OS_FIELD_ID='1002',
    )
    def test_contact_submit_name_defaults_to_email_when_not_provided(self, mock_parse_ua, mock_client_cls):
        """Test that when name is not provided in the payload, it defaults to the email address."""
        mock_parse_ua.return_value = ('Firefox 120', 'macOS 14')

        instance = Mock()
        mock_client_cls.return_value = instance

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = True
        instance.update_ticket.return_value = update_resp

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        response = self.client.post(
            url,
            data={'data': json.dumps(payload)},
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

        self.assertEqual(response.status_code, 200)
        # Verify the name field defaults to email when not provided in payload
        instance.create_ticket.assert_called_once_with(
            {
                'ticket_form_id': 42,
                'name': 'user@example.org',
                'email': 'user@example.org',
                'subject': 'Hello',
                'description': 'Body',
                'attachments': [],
                'custom_fields': [],
            }
        )
        instance.update_ticket.assert_called_once()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    @patch('thunderbird_accounts.support.views.parse_user_agent_info')
    @override_settings(
        ZENDESK_FORM_ID='42',
        ZENDESK_FORM_BROWSER_FIELD_ID='1001',
        ZENDESK_FORM_OS_FIELD_ID='1002',
    )
    def test_contact_submit_uses_name_from_payload_when_provided(self, mock_parse_ua, mock_client_cls):
        """Test that when name is provided in the payload, it uses that name instead of defaulting to email."""
        mock_parse_ua.return_value = ('Firefox 120', 'macOS 14')

        instance = Mock()
        mock_client_cls.return_value = instance

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = True
        instance.update_ticket.return_value = update_resp

        url = reverse('contact_submit')
        payload = {
            'email': 'user@example.org',
            'name': 'John Doe',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        response = self.client.post(
            url,
            data={'data': json.dumps(payload)},
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

        self.assertEqual(response.status_code, 200)
        # Verify the name field uses the provided name from payload
        args, _kwargs = instance.create_ticket.call_args
        sent_fields = args[0]
        self.assertEqual(sent_fields['name'], 'John Doe')
        self.assertEqual(sent_fields['email'], 'user@example.org')
        instance.update_ticket.assert_called_once()


class ZendeskPlanStatusTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='plan@example.org', oidc_id='plan-1')

    def add_subscription(self, paddle_id, status):
        Subscription.objects.create(paddle_id=paddle_id, paddle_customer_id='cus', status=status, user=self.user)

    def test_no_subscription_is_signing_up(self):
        self.assertEqual(get_plan_status_for_zendesk(self.user), 'tm_plan_signingup')

    def test_active_subscription_is_paid(self):
        self.add_subscription('sub1', Subscription.StatusValues.ACTIVE)
        self.assertEqual(get_plan_status_for_zendesk(self.user), 'tm_plan_paid')

    def test_canceled_subscription_is_cancelled(self):
        self.add_subscription('sub1', Subscription.StatusValues.CANCELED)
        self.assertEqual(get_plan_status_for_zendesk(self.user), 'tm_plan_cancelled')

    def test_active_wins_over_canceled(self):
        self.add_subscription('sub1', Subscription.StatusValues.CANCELED)
        self.add_subscription('sub2', Subscription.StatusValues.ACTIVE)
        self.assertEqual(get_plan_status_for_zendesk(self.user), 'tm_plan_paid')

    def test_other_statuses_are_signing_up(self):
        self.add_subscription('sub1', Subscription.StatusValues.PAST_DUE)
        self.assertEqual(get_plan_status_for_zendesk(self.user), 'tm_plan_signingup')


@override_settings(
    ZENDESK_FORM_ID='42',
    ZENDESK_FORM_BROWSER_FIELD_ID='1001',
    ZENDESK_FORM_OS_FIELD_ID='1002',
    ZENDESK_USER_PLAN_STATUS_FIELD_KEY='tm_plan_status',
    ALLOWED_EMAIL_DOMAINS=[MANAGED_DOMAIN],
    CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=False,
)
class ZendeskContactSubmitUserTestCase(TestCase):
    """Tests for the Zendesk user update (external id + plan status) done before ticket creation."""

    def setUp(self):
        cache.clear()
        self.client = RequestClient()
        self.user = User.objects.create(username='known@example.org', oidc_id='known-1')
        self.url = reverse('contact_submit')
        self.payload = {
            'email': 'known@example.org',
            'name': 'Known User',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }

    def mock_client(self, mock_client_cls, user_ok=True):
        instance = Mock()
        mock_client_cls.return_value = instance

        user_resp = Mock()
        user_resp.ok = user_ok
        instance.create_or_update_user.return_value = user_resp

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = True
        instance.update_ticket.return_value = update_resp

        tags_resp = Mock()
        tags_resp.ok = True
        instance.add_ticket_tags.return_value = tags_resp
        return instance

    def submit(self):
        return self.client.post(
            self.url,
            data={'data': json.dumps(self.payload)},
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_logged_in_user_is_updated_before_ticket_creation(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        Subscription.objects.create(
            paddle_id='sub1', paddle_customer_id='cus', status=Subscription.StatusValues.ACTIVE, user=self.user
        )
        self.client.force_login(self.user)

        response = self.submit()

        self.assertEqual(response.status_code, 200)
        instance.create_or_update_user.assert_called_once_with(
            {
                'name': 'Known User',
                'email': 'known@example.org',
                'external_id': str(self.user.uuid),
                'user_fields': {'tm_plan_status': 'tm_plan_paid'},
            }
        )

        # The user has to be updated before the ticket is created
        call_names = [call[0] for call in instance.method_calls]
        self.assertLess(call_names.index('create_or_update_user'), call_names.index('create_ticket'))

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_logged_out_external_address_does_not_update_user(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        self.payload['email'] = 'visitor@external.example'

        response = self.submit()

        self.assertEqual(response.status_code, 200)
        instance.create_or_update_user.assert_not_called()
        instance.create_ticket.assert_called_once()

    @patch('thunderbird_accounts.support.views.sentry_sdk')
    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_user_update_failure_does_not_block_ticket(self, mock_client_cls, mock_sentry):
        instance = self.mock_client(mock_client_cls, user_ok=False)
        self.client.force_login(self.user)

        response = self.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {'success': True})
        instance.create_ticket.assert_called_once()
        mock_sentry.capture_message.assert_called_once()


@override_settings(
    ZENDESK_FORM_ID='42',
    ZENDESK_FORM_BROWSER_FIELD_ID='1001',
    ZENDESK_FORM_OS_FIELD_ID='1002',
    ZENDESK_USER_PLAN_STATUS_FIELD_KEY='tm_plan_status',
    ZENDESK_TAG_IDENTITY_VERIFIED='thundermail_accounts_identity_verified',
    ZENDESK_TAG_IDENTITY_UNVERIFIED='thundermail_accounts_identity_unverified',
    ALLOWED_EMAIL_DOMAINS=[MANAGED_DOMAIN],
    CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=False,
)
class ContactSubmitIdentityTestCase(TestCase):
    """Managed-domain requester addresses must belong to the signed-in user, and every ticket is tagged
    with whether the requester address was verified."""

    def setUp(self):
        cache.clear()
        self.client = RequestClient()
        self.url = reverse('contact_submit')

        self.owner = User.objects.create(
            username=f'owner@{MANAGED_DOMAIN}',
            email=f'owner@{MANAGED_DOMAIN}',
            recovery_email='owner-recovery@external.example',
            oidc_id='owner-1',
        )
        owner_account = Account.objects.create(name=self.owner.username, user=self.owner)
        Email.objects.create(address=self.owner.username, type=Email.EmailType.PRIMARY, account=owner_account)
        self.owner_alias = f'owner-alias@{MANAGED_DOMAIN}'
        Email.objects.create(address=self.owner_alias, type=Email.EmailType.ALIAS, account=owner_account)

        self.other = User.objects.create(
            username=f'other@{MANAGED_DOMAIN}',
            email=f'other@{MANAGED_DOMAIN}',
            oidc_id='other-1',
        )
        other_account = Account.objects.create(name=self.other.username, user=self.other)
        Email.objects.create(address=self.other.username, type=Email.EmailType.PRIMARY, account=other_account)

    def mock_client(self, mock_client_cls, tags_ok=True):
        instance = Mock()
        mock_client_cls.return_value = instance

        instance.upload_file.return_value = {'success': True, 'upload_token': 'tok123', 'filename': 'test.txt'}

        user_resp = Mock()
        user_resp.ok = True
        instance.create_or_update_user.return_value = user_resp

        create_resp = Mock()
        create_resp.ok = True
        create_resp.json.return_value = {'request': {'id': 555}}
        instance.create_ticket.return_value = create_resp

        update_resp = Mock()
        update_resp.ok = True
        instance.update_ticket.return_value = update_resp

        tags_resp = Mock()
        tags_resp.ok = tags_ok
        tags_resp.status_code = 200 if tags_ok else 500
        instance.add_ticket_tags.return_value = tags_resp
        return instance

    def submit(self, email, attachment=None):
        payload = {
            'email': email,
            'name': 'Someone',
            'fields': [
                {'id': 11, 'title': 'Subject', 'type': 'subject', 'value': 'Hello', 'required': True},
                {'id': 12, 'title': 'Description', 'type': 'description', 'value': 'Body', 'required': True},
            ],
        }
        data = {'data': json.dumps(payload)}
        if attachment is not None:
            data['attachments'] = attachment
        return self.client.post(
            self.url,
            data=data,
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

    def assert_no_zendesk_calls(self, instance):
        instance.upload_file.assert_not_called()
        instance.create_or_update_user.assert_not_called()
        instance.create_ticket.assert_not_called()
        instance.update_ticket.assert_not_called()
        instance.add_ticket_tags.assert_not_called()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_logged_out_managed_address_is_rejected_before_any_zendesk_call(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        uploaded = SimpleUploadedFile('test.txt', b'hi', content_type='text/plain')

        response = self.submit(self.other.username, attachment=uploaded)

        self.assertEqual(response.status_code, 403)
        self.assertIn('please sign in', response.json()['detail'])
        self.assert_no_zendesk_calls(instance)

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_logged_in_other_users_managed_address_is_rejected(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        self.client.force_login(self.owner)

        response = self.submit(self.other.username)

        self.assertEqual(response.status_code, 403)
        self.assertIn("isn't on your account", response.json()['detail'])
        self.assert_no_zendesk_calls(instance)

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_logged_in_own_address_is_accepted_as_typed_and_tagged_verified(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        self.client.force_login(self.owner)
        as_typed = f'  Owner@{MANAGED_DOMAIN.title()} '

        response = self.submit(as_typed)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})
        # The ownership check is case-insensitive, but Zendesk receives the address as typed (stripped)
        self.assertEqual(instance.create_ticket.call_args.args[0]['email'], as_typed.strip())
        instance.add_ticket_tags.assert_called_once_with(555, ['thundermail_accounts_identity_verified'])

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_external_address_is_accepted_and_tagged_unverified(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        self.client.force_login(self.owner)

        response = self.submit('someone@external.example')

        self.assertEqual(response.status_code, 200)
        instance.create_ticket.assert_called_once()
        instance.add_ticket_tags.assert_called_once_with(555, ['thundermail_accounts_identity_unverified'])

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_tag_failure_does_not_block_success(self, mock_client_cls):
        self.mock_client(mock_client_cls, tags_ok=False)
        self.client.force_login(self.owner)

        with self.assertLogs('thunderbird_accounts.support.views', level='ERROR') as logs:
            response = self.submit(self.owner.username)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})
        self.assertTrue(any('[contact_submit]' in line and '555' in line for line in logs.output))

    @override_settings(CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=True, USE_ALLOW_LIST=True)
    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_allow_list_is_enforced_server_side(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)

        response = self.submit('stranger@external.example')

        self.assertEqual(response.status_code, 403)
        self.assertIn("isn't linked to a Thundermail account", response.json()['detail'])
        self.assert_no_zendesk_calls(instance)

    @override_settings(CONTACT_SUPPORT_ONLY_FOR_ALLOW_LISTED_USERS=True, USE_ALLOW_LIST=True)
    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_own_alias_bypasses_allow_list(self, mock_client_cls):
        instance = self.mock_client(mock_client_cls)
        self.client.force_login(self.owner)

        response = self.submit(self.owner_alias)

        self.assertEqual(response.status_code, 200)
        instance.create_ticket.assert_called_once()

    @patch('thunderbird_accounts.support.views.ZendeskClient')
    def test_submissions_are_throttled(self, mock_client_cls):
        self.mock_client(mock_client_cls)

        for _ in range(5):
            self.assertEqual(self.submit('someone@external.example').status_code, 200)

        response = self.submit('someone@external.example')

        self.assertEqual(response.status_code, 429)

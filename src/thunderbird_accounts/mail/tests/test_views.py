import json
from unittest.mock import patch, Mock

from django.conf import settings
from django.test import TestCase, Client as RequestClient, override_settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.files.uploadedfile import SimpleUploadedFile

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account


class HomeViewRedirectTestCase(TestCase):
    """Test redirect behavior for authenticated and unauthenticated users."""

    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)

    def test_unauthenticated_user_redirected_to_login_for_home(self):
        """Test that unauthenticated users are redirected to login when accessing home."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

    def test_unauthenticated_user_redirected_to_login_for_non_public_routes(self):
        """Test that unauthenticated users are redirected to login for non-public routes."""
        non_public_paths = ['/dashboard', '/mail', '/some-other-path']
        for path in non_public_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse('login'))

    def test_unauthenticated_user_can_access_privacy_page(self):
        """Test that unauthenticated users can access the /privacy public route."""
        response = self.client.get('/privacy')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mail/index.html')

    def test_unauthenticated_user_can_access_terms_page(self):
        """Test that unauthenticated users can access the /terms public route."""
        response = self.client.get('/terms')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mail/index.html')

    def test_authenticated_user_can_access_home(self):
        """Test that authenticated users can access home without redirect."""
        self.client.force_login(self.user)

        # Mock OIDC session data to prevent SessionRefresh middleware from redirecting
        session = self.client.session
        session['oidc_id_token_expiration'] = 9999999999  # Far future timestamp
        session.save()

        with patch('thunderbird_accounts.mail.views.MailClient') as mock_mail_client:
            mock_instance = Mock()
            mock_instance.get_account.return_value = {
                'description': 'Test User',
                'secrets': [],
                'emails': [f'test@{settings.PRIMARY_EMAIL_DOMAIN}'],
            }
            mock_mail_client.return_value = mock_instance

            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'mail/index.html')

    def test_authenticated_user_can_access_any_path(self):
        """Test that authenticated users can access any path without redirect."""
        self.client.force_login(self.user)

        # Mock OIDC session data to prevent SessionRefresh middleware from redirecting
        session = self.client.session
        session['oidc_id_token_expiration'] = 9999999999  # Far future timestamp
        session.save()

        paths = ['/dashboard', '/mail', '/privacy', '/terms']

        for path in paths:
            with self.subTest(path=path):
                with patch('thunderbird_accounts.mail.views.MailClient') as mock_mail_client:
                    mock_instance = Mock()
                    mock_instance.get_account.return_value = {
                        'description': 'Test User',
                        'secrets': [],
                        'emails': [f'test@{settings.PRIMARY_EMAIL_DOMAIN}'],
                    }
                    mock_mail_client.return_value = mock_instance

                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'mail/index.html')


class AddEmailAliasTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()
        self.user = User.objects.create(username=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', oidc_id='1234')
        self.account = Account.objects.create(name=f'test@{settings.PRIMARY_EMAIL_DOMAIN}', user=self.user)
        self.client.force_login(self.user)

    def test_success(self):
        email_alias_url = reverse('add_email_alias')

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'buddy', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode()), {'success': True})

    def test_reserved(self):
        email_alias_url = reverse('add_email_alias')

        with patch('thunderbird_accounts.mail.views.MailClient', Mock()) as mock:
            instance = Mock()
            mock.save_email_addresses = instance
            response = self.client.post(
                email_alias_url,
                data={'email-alias': 'admin', 'domain': settings.PRIMARY_EMAIL_DOMAIN},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                json.loads(response.content.decode()),
                {'success': False, 'error': _('You cannot use this email address.')},
            )


class ZendeskContactFieldsTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
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


class ZendeskContactSubmitTestCase(TestCase):
    def setUp(self):
        self.client = RequestClient()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    @patch('thunderbird_accounts.utils.utils.parse_user_agent_info')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    @override_settings(ZENDESK_FORM_ID='42')
    def test_contact_submit_upload_exception(self, mock_client_cls):
        instance = Mock()
        mock_client_cls.return_value = instance
        instance.upload_file.side_effect = Exception('boom')

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
        self.assertIn('Failed to upload file test.txt: boom', body['error'])
        instance.create_ticket.assert_not_called()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    @patch('thunderbird_accounts.utils.utils.parse_user_agent_info')
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

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    @patch('thunderbird_accounts.utils.utils.parse_user_agent_info')
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
            ],
        }
        response = self.client.post(
            url,
            data={'data': json.dumps(payload)},
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/120.0',
        )

        self.assertEqual(response.status_code, 200)
        # Verify the name field defaults to email when not provided in payload
        instance.create_ticket.assert_called_once_with({
            'ticket_form_id': 42,
            'name': 'user@example.org',
            'email': 'user@example.org',
            'subject': 'Hello',
            'description': 'Body',
            'attachments': [],
            'custom_fields': [],
        })
        instance.update_ticket.assert_called_once()

    @patch('thunderbird_accounts.mail.views.ZendeskClient')
    @patch('thunderbird_accounts.utils.utils.parse_user_agent_info')
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
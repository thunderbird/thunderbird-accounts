from django.contrib.auth.models import AnonymousUser
from thunderbird_accounts.subscription.models import Subscription
from thunderbird_accounts.mail.models import Account
from django.conf import settings
from importlib import import_module
from typing import Optional
from django.contrib.sessions.backends.base import SessionBase
from django.http.request import HttpRequest
from unittest.mock import MagicMock
from thunderbird_accounts.mail.middleware import FixMissingArchivesFolderMiddleware
from thunderbird_accounts.authentication.models import User
from django.test.testcases import TestCase
from unittest.mock import patch


@patch('thunderbird_accounts.mail.tiny_jmap_client.TinyJMAPClient')
class FixMissingArchivesFolderMiddlewareTestCase(TestCase):
    DEFAULT_TEMP_ID = 'abc123'

    def setUp(self):
        self.fake_response = MagicMock()
        self.middleware = FixMissingArchivesFolderMiddleware(self.fake_response)

    def build_mailbox_query_response(self, mailbox_ids: Optional[list] = None) -> dict:
        return {
            'methodResponses': [
                [
                    'Mailbox/query',
                    {
                        'accountId': 'd',
                        'queryState': 'sai',
                        'canCalculateChanges': True,
                        'position': 0,
                        'ids': ['a'] if not mailbox_ids else mailbox_ids,
                    },
                    'a',
                ]
            ],
            'sessionState': '3e25b2a0',
        }

    def build_mailbox_set_response(self, temp_id: Optional[str] = None, mailbox_id: Optional[str] = None) -> dict:
        if not temp_id:
            temp_id = self.DEFAULT_TEMP_ID
        return {
            'methodResponses': [
                [
                    'Mailbox/set',
                    {
                        'accountId': 'e',
                        'oldState': 'sae',
                        'newState': 'sai',
                        'created': {temp_id: {'id': 'h' if not mailbox_id else mailbox_id}},
                    },
                    '0',
                ]
            ],
            'sessionState': '3e25b2a0',
        }

    def build_request(self, user: Optional[User] = None, access_token: Optional[str] = None):
        fake_request = HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        fake_request.session = engine.SessionStore()

        if access_token:
            fake_request.session['oidc_access_token'] = access_token

        if user:
            fake_request.user = user
        else:
            fake_request.user = AnonymousUser()

        fake_request.session.save()
        return fake_request

    def test_freshly_subscribed_user(self, tiny_jmap_mock: MagicMock):
        """A fresh user who has a subscription and a stalwart account should have their archive folder checked
        and successfully created"""
        oidc_access_token = 'abc123'

        user = User(username='test@example.org', email='test@example.com')
        user.save()

        # We need a stalwart reference
        account = Account(name=user.username, user=user)
        account.save()
        self.assertFalse(account.verified_archive_folder)

        # We need an "active" subscription
        sub = Subscription(
            paddle_id='foo', paddle_customer_id='bar', status=Subscription.StatusValues.ACTIVE, user=user
        )
        sub.save()

        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        # First request is query, second is set
        make_jmap_call.side_effect = [self.build_mailbox_query_response(), self.build_mailbox_set_response()]

        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        # Fake a request with a logged in user and oidc_access_token
        fake_request = self.build_request(user, oidc_access_token)

        # Run the middleware
        self.middleware(fake_request)

        # Ensure make_jmap_call was called
        make_jmap_call.assert_called()

        # Ensure account now has verified_archive_folder as true
        account.refresh_from_db()
        self.assertTrue(account.verified_archive_folder)

    def test_already_verified_account_isnt_checked_again(self, tiny_jmap_mock: MagicMock):
        """A user with a verified archive folder shouldn't have any jmap calls sent"""
        oidc_access_token = 'abc123'

        user = User(username='test@example.org', email='test@example.com')
        user.save()

        # We need a stalwart reference, we'll start by marking it as verified
        account = Account(name=user.username, user=user, verified_archive_folder=True)
        account.save()
        self.assertTrue(account.verified_archive_folder)

        # We need an "active" subscription
        sub = Subscription(
            paddle_id='foo', paddle_customer_id='bar', status=Subscription.StatusValues.ACTIVE, user=user
        )
        sub.save()

        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        # Fake a request with a logged in user and oidc_access_token
        fake_request = self.build_request(user, oidc_access_token)

        # Run the middleware
        self.middleware(fake_request)

        # Ensure make_jmap_call was called
        make_jmap_call.assert_not_called()

        # Ensure account verified_archive_folder is still true
        account.refresh_from_db()
        self.assertTrue(account.verified_archive_folder)

    @patch('thunderbird_accounts.mail.utils.fix_archives_folder')
    def test_unauthenticated_user_shouldnt_have_fix_archives_folder_called(
        self, tiny_jmap_mock: MagicMock, fix_archives_folder_mock: MagicMock
    ):
        """A unauthenticated user shouldn't have fix archives folder called"""
        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        fake_request = self.build_request(None, None)

        # Run the middleware
        self.middleware(fake_request)

        # Make sure neither jmap calls were sent out, and that our fix archive folder wasn't either.
        fix_archives_folder_mock.assert_not_called()
        make_jmap_call.assert_not_called()

    @patch('thunderbird_accounts.mail.utils.fix_archives_folder')
    def test_authenticated_but_not_subscribed_user_shouldnt_have_fix_archives_folder_called(
        self, tiny_jmap_mock: MagicMock, fix_archives_folder_mock: MagicMock
    ):
        """An authenticated but non-subscribed user shouldn't ahve fix archives folder called"""
        oidc_access_token = 'abc123'

        user = User(username='test@example.org', email='test@example.com')
        user.save()

        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        fake_request = self.build_request(user, oidc_access_token)

        # Run the middleware
        self.middleware(fake_request)

        # Make sure neither jmap calls were sent out, and that our fix archive folder wasn't either.
        fix_archives_folder_mock.assert_not_called()
        make_jmap_call.assert_not_called()

    @patch('thunderbird_accounts.mail.utils.fix_archives_folder')
    def test_non_active_subscription_shouldnt_have_fix_archives_folder_called(
        self, tiny_jmap_mock: MagicMock, fix_archives_folder_mock: MagicMock
    ):
        """An authenticated user with a non-active subscription shouldn't ahve fix archives folder called"""
        oidc_access_token = 'abc123'

        user = User(username='test@example.org', email='test@example.com')
        user.save()

        # We need a stalwart reference, we'll start by marking it as verified
        account = Account(name=user.username, user=user)
        account.save()
        self.assertFalse(account.verified_archive_folder)

        # We need an "active" subscription
        sub = Subscription(
            paddle_id='foo', paddle_customer_id='bar', status=Subscription.StatusValues.CANCELED, user=user
        )
        sub.save()

        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        fake_request = self.build_request(user, oidc_access_token)

        # Run the middleware
        self.middleware(fake_request)

        # Make sure neither jmap calls were sent out, and that our fix archive folder wasn't either.
        fix_archives_folder_mock.assert_not_called()
        make_jmap_call.assert_not_called()

    def test_malformed_jmap_response_shouldnt_crash_the_request(self, tiny_jmap_mock: MagicMock):
        """An authenticated user with a non-active subscription shouldn't ahve fix archives folder called"""
        oidc_access_token = 'abc123'

        user = User(username='test@example.org', email='test@example.com')
        user.save()

        # We need a stalwart reference, we'll start by marking it as verified
        account = Account(name=user.username, user=user)
        account.save()
        self.assertFalse(account.verified_archive_folder)

        # We need an "active" subscription
        sub = Subscription(
            paddle_id='foo', paddle_customer_id='bar', status=Subscription.StatusValues.ACTIVE, user=user
        )
        sub.save()

        # Mock tiny_jmap
        tiny_jmap_mock_instance = tiny_jmap_mock()
        make_jmap_call = MagicMock()
        make_jmap_call.return_value = {'this is garbage': 'woohoo!'}
        tiny_jmap_mock_instance.make_jmap_call = make_jmap_call

        fake_request = self.build_request(user, oidc_access_token)

        # Run the middleware
        self.middleware(fake_request)

        # Make sure neither jmap calls were sent out, and that our fix archive folder wasn't either.
        make_jmap_call.assert_called()

        # Ensure account verified_archive_folder is still false
        account.refresh_from_db()
        self.assertFalse(account.verified_archive_folder)

from typing import Optional
from django.contrib.sessions.backends.base import SessionBase
from django.http.request import HttpRequest
from unittest.mock import MagicMock
from thunderbird_accounts.mail.middleware import FixMissingArchivesFolderMiddleware
from thunderbird_accounts.authentication.models import User
from django.test.testcases import TestCase
from unittest.mock import patch

@patch('thunderbird_accounts.mail.utils.TinyJMAPClient')
class FixMissingArchivesFolderMiddlewareTestCase(TestCase):
    def setUp(self):
        self.fake_response = MagicMock()
        self.middleware = FixMissingArchivesFolderMiddleware(self.fake_response)

    def build_request(self, user: Optional[User] = None, access_token: Optional[str] = None):
        fake_request = HttpRequest()
        fake_request.session = SessionBase()
        if access_token:
            fake_request.session['oidc_access_token'] = access_token
        if user:
            fake_request.user = user
        fake_request.session.save()
        return fake_request

    def test_freshly_subscribed_user(self, tiny_jmap_mock: MagicMock):
        user = User(username='test@example.org', email='test@example.com')
        user.save()

        oidc_access_token = 'abc123'

        fake_request = self.build_request(user, oidc_access_token)
        self.middleware(fake_request)

        tiny_jmap_mock.make_jmap_call.return_value = {}

        print('fin!')

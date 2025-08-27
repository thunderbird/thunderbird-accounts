import freezegun
from django.conf import settings
from django.test import TestCase, Client as RequestClient
from django.urls import reverse

from thunderbird_accounts.authentication.middleware import AccountsOIDCBackend
from thunderbird_accounts.authentication.models import User


class AccountsOIDCBackendTestCase(TestCase):
    def setUp(self):
        self.claim_oidc_id = 'abc123'
        self.claim_email = 'user@example.org'
        with freezegun.freeze_time('Apr 4th, 2000'):
            self.user = User.objects.create(
                oidc_id=self.claim_oidc_id, username='test@example.org', email=self.claim_email
            )
            self.user.save()
            self.user.refresh_from_db()
        self.backend = AccountsOIDCBackend()

    def test_filter_users_by_claims_no_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = False

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 0

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})
        assert len(query) == 1

        query = self.backend.filter_users_by_claims(
            {'sub': f'{self.claim_oidc_id}_not_the_actual_id_anymore', 'email': self.claim_email}
        )
        assert len(query) == 1

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting

    def test_filter_users_by_claims_with_fallback_with_duplicates(self):
        _original_setting = settings.OIDC_FALLBACK_MATCH_BY_EMAIL
        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = True

        # Ensure the user doesn't have an oidc id
        self.user.oidc_id = None
        self.user.save()

        user_duplicates = [
            User.objects.create(oidc_id=None, email=self.claim_email, username='test'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test2'),
            User.objects.create(oidc_id=None, email=self.claim_email, username='test3'),
        ]

        query = self.backend.filter_users_by_claims({'sub': self.claim_oidc_id, 'email': self.claim_email})

        assert len(query) == 1
        self.assertEqual(self.user.pk, query[0].pk)
        self.assertEqual(self.claim_email, query[0].email)

        # Ensure the older models were deleted
        for user in user_duplicates:
            with self.assertRaises(User.DoesNotExist):
                user.refresh_from_db()

        settings.OIDC_FALLBACK_MATCH_BY_EMAIL = _original_setting


class LoginRequiredTestCase(TestCase):
    # (URL reverse key, expected response status code),
    login_required_keys = [
        ('self_serve_dashboard', 302),
        ('self_serve_account_info', 302),
        ('self_serve_app_password', 302),
        ('self_serve_connection_info', 302),
        ('self_serve_subscription', 302),
        ('self_serve_subscription_success', 302),
    ]

    def test_logged_out(self):
        client = RequestClient()
        login_url = reverse(settings.LOGIN_URL)

        for key, _ in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(login_url))

    def test_logged_in(self):
        client = RequestClient()
        user = User.objects.get_or_create(username='test', oidc_id='1234')[0]
        client.force_login(user)

        for key, status in self.login_required_keys:
            url = reverse(key)
            self.assertTrue(url)

            response = client.get(url, follow=False)
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.request['PATH_INFO'].startswith(url))

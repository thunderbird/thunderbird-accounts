from django.conf import settings
from django.test import TestCase, Client as RequestClient
from django.urls import reverse


from thunderbird_accounts.authentication.models import User


class LoginRequiredTestCase(TestCase):
    # (URL reverse key, expected response status code),
    login_required_keys = [
        ('self_serve_home', 302),  # This one is a redirect
        ('self_serve_account_info', 200),
        ('self_serve_app_password', 200),
        ('self_serve_connection_info', 200),
        ('self_serve_subscription', 200),
        ('self_serve_subscription_success', 200),
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

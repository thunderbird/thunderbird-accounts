from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model


class TestMail(TestCase):
    def setUp(self):
      cache.clear()
      self.c = Client(enforce_csrf_checks=False)
      UserModel = get_user_model()
      self.user = UserModel.objects.create(fxa_id='abc123', email='user@test.com')

    def tearDown(self):
      cache.clear()
  
    def test_sign_up_successful(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': 'tb.pro',
            'app_password': 'password',
        })

      # expect redirect to connection-info after email created successfully
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/self-serve/connection-info')

    def test_sign_up_missing_email(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': '',
            'email_domain': 'tb.pro',
            'app_password': 'password',
        })

      # expect redirect back to /sign-up since required data missing
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_missing_domain(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': '',
            'app_password': 'password',
        })

      # expect redirect back to /sign-up since required data missing
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_missing_password(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': 'tb.pro',
            'app_password': '',
        })

      # expect redirect back to /sign-up since required data missing
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_invalid_domain(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': 'nope.invalid.domain.com',
            'app_password': 'password',
        })

      # expect redirect back to /sign-up since required data missing
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_already_have_account(self):
      self.c.force_login(self.user)

      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': 'tb.pro',
            'app_password': 'password',
        })

      # expect redirect to connection-info after email created successfully
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/self-serve/connection-info')

      # now attempt to sign up for email again
      resp = self.c.post(reverse('sign_up_submit'), data={
            'email_address': 'new-thundermail-address',
            'email_domain': 'tb.pro',
            'app_password': 'password',
        })

      # expect redirect back to /sign-up since already signed up
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_submit_no_user(self):
      resp = self.c.post(reverse('sign_up_submit'))
      # expect no user redirect to root b/c no user
      self.assertEqual(resp.status_code, 302)
      self.assertEqual(resp.url, '/')

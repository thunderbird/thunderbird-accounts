from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model

from thunderbird_accounts.mail.models import Email, Account


class TestMail(TestCase):
    def setUp(self):
        cache.clear()
        self.c = Client(enforce_csrf_checks=False)
        self.UserModel = get_user_model()
        self.user = self.UserModel.objects.create(fxa_id='abc123', email='user@test.com')
        self.sign_up_data = {
            'email_address': 'new-thundermail-address',
            'email_domain': settings.ALLOWED_EMAIL_DOMAINS[0],
            'app_password': 'password',
        }
        self.sign_up_full_email = f'{self.sign_up_data["email_address"]}@{self.sign_up_data["email_domain"]}'

    def tearDown(self):
        cache.clear()

    def does_account_exist(self, account_name):
        # check if given account exists in the db
        try:
            Account.objects.get(name=account_name)
            return True
        except Account.DoesNotExist:
            pass
        return False

    def does_email_exist(self, account_name, email_to_check):
        # check if given email exists in the db
        try:
            Email.objects.get(name=account_name, address=email_to_check)
            return True
        except Email.DoesNotExist:
            pass
        return False

    def test_sign_up_successful(self):
        self.c.force_login(self.user)

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect to connection-info after email created successfully
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/self-serve/connection-info')

        # verify account and email were added to db
        self.assertTrue(self.does_account_exist(self.user.email))
        self.assertTrue(self.does_email_exist(self.user.email, self.sign_up_full_email))

    def test_sign_up_missing_email(self):
        self.c.force_login(self.user)
        self.sign_up_data['email_address'] = ''

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since required data missing
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_missing_domain(self):
        self.c.force_login(self.user)
        self.sign_up_data['email_domain'] = ''

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since required data missing
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_missing_password(self):
        self.c.force_login(self.user)
        self.sign_up_data['app_password'] = ''

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since required data missing
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_invalid_domain(self):
        self.c.force_login(self.user)
        self.sign_up_data['email_domain'] = 'nope.invalid.domain.com'

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since required data missing
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_already_have_account(self):
        self.c.force_login(self.user)

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect to connection-info after email created successfully
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/self-serve/connection-info')

        # now attempt to sign up for email again
        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since already signed up
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

    def test_sign_up_submit_no_user(self):
        resp = self.c.post(reverse('sign_up_submit'))

        # expect no user redirect to root b/c no user
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/')

    def test_sign_up_email_already_taken(self):
        self.c.force_login(self.user)

        resp = self.c.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect to connection-info after email created successfully
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/self-serve/connection-info')

        # verify account and email were added to db
        self.assertTrue(self.does_account_exist(self.user.email))
        self.assertTrue(self.does_email_exist(self.user.email, self.sign_up_full_email))

        # now create a 2nd user
        second_client = Client(enforce_csrf_checks=False)
        second_user = self.UserModel.objects.create(
            fxa_id='abc456', email='second-user@test.com', username='Second User'
        )

        second_client.force_login(second_user)

        # then have the 2nd user attempt to sign up for email using the same email address
        resp = second_client.post(reverse('sign_up_submit'), data=self.sign_up_data)

        # expect redirect back to /sign-up since sign up should fail b/c requested email address is not unique
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/sign-up/')

        # verify account and email weren't added to db
        self.assertFalse(self.does_account_exist(second_user.email))
        self.assertFalse(self.does_email_exist(second_user.email, self.sign_up_full_email))

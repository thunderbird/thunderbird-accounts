from unittest.mock import patch

from django.conf import settings
from django.forms import inlineformset_factory, modelform_factory
from django.test import TestCase

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.admin.forms import (
    ASTERISK_NOT_ALLOWED_ERROR,
    CustomAccountBaseForm,
    CustomEmailBaseForm,
)
from thunderbird_accounts.mail.models import Account, Email


class CustomAccountBaseFormTestCase(TestCase):
    def test_rejects_name_with_asterisk(self):
        form_class = modelform_factory(Account, form=CustomAccountBaseForm, fields=['name'])
        form = form_class({'name': f'aa*@{settings.PRIMARY_EMAIL_DOMAIN}'})

        self.assertFalse(form.is_valid())
        self.assertIn(ASTERISK_NOT_ALLOWED_ERROR, form.errors['name'])


@patch('thunderbird_accounts.mail.admin.forms.utils.add_email_addresses_to_stalwart_account')
class CustomEmailBaseFormTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username=f'hello@{settings.PRIMARY_EMAIL_DOMAIN}')
        self.account = Account.objects.create(name=self.user.username, user=self.user)
        self.formset_class = inlineformset_factory(
            Account, Email, formset=CustomEmailBaseForm, fields=['address', 'type'], extra=1
        )

    def _build_formset(self, address: str):
        return self.formset_class(
            {
                'email_set-TOTAL_FORMS': '1',
                'email_set-INITIAL_FORMS': '0',
                'email_set-0-address': address,
                'email_set-0-type': Email.EmailType.ALIAS.value,
            },
            instance=self.account,
        )

    def test_rejects_address_with_asterisk(self, mock_add_addresses):
        for address in (f'aa*@{settings.PRIMARY_EMAIL_DOMAIN}', '*@customdomain.com'):
            with self.subTest(address=address):
                formset = self._build_formset(address)

                self.assertFalse(formset.is_valid())
                self.assertIn(ASTERISK_NOT_ALLOWED_ERROR, formset.forms[0].errors['address'])

        mock_add_addresses.assert_not_called()

    def test_accepts_address_without_asterisk(self, mock_add_addresses):
        address = f'alias@{settings.PRIMARY_EMAIL_DOMAIN}'
        formset = self._build_formset(address)

        self.assertTrue(formset.is_valid(), formset.errors)
        mock_add_addresses.assert_called_once_with(self.user, [address])

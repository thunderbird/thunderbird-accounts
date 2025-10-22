from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from thunderbird_accounts.mail import utils
from thunderbird_accounts.mail.models import Account, Email


class CustomAccountBaseForm(forms.ModelForm):
    """Base class to use for custom email admin forms."""

    class Meta:
        model = Account
        fields = '__all__'

    def clean(self):
        # TODO: Check for active stalwart / active subscription account here!

        return super().clean()


class CustomEmailBaseForm(forms.BaseInlineFormSet):
    """Base class to use for custom email admin forms."""

    class Meta:
        model = Email
        fields = '__all__'

    def clean(self):
        new_addresses = []
        update_addresses = []
        delete_addresses = []

        user = self.instance.user

        has_errors = False

        for form in self.forms:
            if not form.is_valid() or not form.instance.address or len(form.changed_data) == 0:
                continue

            address = form.instance
            initial_address = form.initial.get('address')

            try:
                validate_email(address.address)
            except ValidationError as ex:
                form.add_error('address', ex)
                has_errors = True
                continue

            if not initial_address:
                new_addresses = [address.address]
            elif 'DELETE' in form.changed_data:
                delete_addresses = [initial_address]
            elif initial_address != address.address:
                update_addresses = [(initial_address, address.address)]

        # Don't do anything because we have errors on the form!
        if has_errors:
            return super().clean()

        if len(new_addresses) > 0:
            utils.add_email_addresses_to_stalwart_account(user, new_addresses)
        if len(update_addresses) > 0:
            utils.replace_email_addresses_on_stalwart_account(user, update_addresses)
        if len(delete_addresses) > 0:
            utils.delete_email_addresses_from_stalwart_account(user, delete_addresses)

        return super().clean()

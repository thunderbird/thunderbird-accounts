import logging

from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext as _

from thunderbird_accounts.core.utils import get_absolute_url
from thunderbird_accounts.mail.models import Domain


def send_domain_verification_result_email(domain: Domain):
    """Emails the domain's owner whether the domain is now verified, with a link to their settings."""
    user = domain.user
    if not user.email:
        logging.warning(f'[send_domain_verification_result_email] User {user.uuid} has no email address, skipping.')
        return

    settings_url = get_absolute_url('/settings')

    # We don't have i18n setup properly just yet / no strings in other languages
    # but leaving this here so it is more or less ready when we do have it
    with translation.override(user.language):
        if domain.status == Domain.DomainStatus.VERIFIED:
            subject = _('Your domain %(domain)s has been verified') % {'domain': domain.name}
            body = _(
                'Your custom domain %(domain)s has been verified.\n\nView your domain in your settings: %(url)s\n'
            ) % {
                'domain': domain.name,
                'url': settings_url,
            }
        else:
            subject = _('Verification of your domain %(domain)s failed') % {'domain': domain.name}
            body = _(
                'We could not verify your custom domain %(domain)s.\n\n'
                'Review your DNS records and try again from your settings: %(url)s\n'
            ) % {'domain': domain.name, 'url': settings_url}

    send_mail(subject, body, None, [user.email])

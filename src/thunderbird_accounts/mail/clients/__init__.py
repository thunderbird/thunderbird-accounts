from django.conf import settings
from . import mail_client_interface
from . import mail_client_legacy
from . import mail_client_jmap

# Hack to fix imports for now
MailClient = (
    mail_client_legacy.MailClientLegacy
    if not settings.STALWART_ADMIN_API_USE_JMAP
    else mail_client_jmap.MailClientAdminJMAP
)
DomainVerificationErrors = mail_client_legacy.DomainVerificationErrors
StaleDNSRecordCode = mail_client_legacy.StaleDNSRecordCode
DNSRecordStatus = mail_client_interface.DNSRecordStatus

from . import mail_client_interface
from . import mail_client_legacy

# Hack to fix imports for now
MailClient = mail_client_legacy.MailClientLegacy
DomainVerificationErrors = mail_client_legacy.DomainVerificationErrors
StaleDNSRecordCode = mail_client_legacy.StaleDNSRecordCode
DNSRecordStatus = mail_client_interface.DNSRecordStatus

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class StalwartType(BaseModel):
    """Stalwart uses custom types in the shape of {'@type': 'Type'} (like {'@type': 'Enabled'} 
    in Domain.subAddressing's case)
    
    This is a shape to ingest that, but we don't do any processing on what what might be inside."""

    type: Optional[str] = Field(alias='@type', default=None)

class JMapType(BaseModel):
    id: str


class DomainType(JMapType):
    """Stalwart Domain Type

    Ref: https://stalw.art/docs/ref/object/domain/"""
    name: str
    aliases: dict  # list[str]
    isEnabled: bool
    createdAt: datetime
    description: Optional[str] = None
    logo: Optional[str] = None
    certificateManagement: dict|StalwartType
    dkimManagement: StalwartType
    dnsManagement: StalwartType
    dnsZoneFile: str
    memberTenantId: Optional[str] = None
    directoryId: Optional[str] = None
    catchAllAddress: Optional[str] = None
    subAddressing: StalwartType
    allowRelaying: bool
    reportAddressUri: Optional[str] = None

class AccountType(JMapType, StalwartType):
    """Stalwart Account Type

    .. code-block:: json

        {
          "name": "admin",
          "domainId": "b",
          "credentials": {
            "0": {
              "credentialId": "a",
              "secret": "****",
              "expiresAt": null,
              "allowedIps": {},
              "@type": "Password"
            }
          },
          "createdAt": "2026-07-08T20:45:29Z",
          "memberGroupIds": {},
          "memberTenantId": null,
          "roles": {
            "@type": "Admin"
          },
          "permissions": {
            "@type": "Inherit"
          },
          "quotas": {},
          "aliases": {},
          "description": "System administrator",
          "locale": "en_US",
          "timeZone": null,
          "encryptionAtRest": {
            "@type": "Disabled"
          },
          "@type": "User",
          "usedDiskQuota": 0,
          "emailAddress": "admin@example.org",
          "id": "b"
        }

    Ref: https://stalw.art/docs/ref/object/account/
    """
    name: str
    domainId: str
    emailAddress: str
    credentials: Optional[StalwartType|dict] = None
    createdAt: Optional[datetime] = None
    memberGroupsIds: Optional[list[str]] = None
    memberTenantId: Optional[str] = None
    roles: StalwartType|dict
    permissions: StalwartType
    quotas: Optional[dict] = None
    usedDiskQuota: Optional[int] = None
    aliases: Optional[dict] = None
    description: Optional[str] = None
    locale: Optional[str] = "en_US"
    timezone: Optional[str] = None
    encryptionAtRest: StalwartType

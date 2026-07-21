from enum import StrEnum
from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasPath, AliasChoices

Duration = Annotated[str | int, Field()]
"""A field that takes in either ms as an integer or time followed by the unit as a string
Ref: https://stalw.art/docs/0.15/configuration/values/duration"""


class StalwartType(BaseModel):
    """Stalwart uses custom types in the shape of {'@type': 'Type'} (like {'@type': 'Enabled'}
    in Domain.subAddressing's case)

    This is a shape to ingest that, but we don't do any processing on what what might be inside."""

    model_config = ConfigDict(serialize_by_alias=True)
    type: Optional[str] = Field(validation_alias=AliasChoices('@type', 'type'), serialization_alias='@type', default=None)


class JMapType(BaseModel):
    """Base type for all jmap responses"""

    id: Optional[str] = None


class DnsServer(StalwartType):
    """I'm not writing out all of the types, please reference:
    https://stalw.art/docs/ref/object/dns-server/
    """

    model_config = ConfigDict(polymorphic_serialization=True)

    host: str
    port: int = 53
    keyName: str
    key: str
    protocol: str
    tsigAlgorithm: str
    description: str
    memberTenantId: Optional[str] = None
    timeout: Duration
    ttl: Duration
    pollingInterval: Duration
    propagationTimeout: Duration
    propagationDelay: Optional[Duration] = None


class DkimManagement(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class DkimManagementProperties(DkimManagement):
    """@type = Automatic
    Ref: https://stalw.art/docs/ref/object/domain/#dkimmanagementproperties"""

    algorithms: dict[str, bool]
    selectorTemplate: str
    rotateAfter: Duration
    retireAfter: Duration
    deleteAfter: Duration


class DnsManagement(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class DnsManagementProperties(DnsManagement):
    dnsServerId: str
    origin: Optional[str] = None
    publishRecords: dict


class SubAddressing(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class SubAddressingCustom(StalwartType):
    customRole: dict


class DomainType(JMapType):
    """Stalwart Domain Type

    Ref: https://stalw.art/docs/ref/object/domain/"""

    name: str
    aliases: dict  # list[str]
    isEnabled: bool
    createdAt: datetime
    description: Optional[str] = None
    logo: Optional[str] = None
    certificateManagement: dict | StalwartType
    dkimManagement: DkimManagement | DkimManagementProperties
    dnsManagement: DnsManagement | DnsManagementProperties
    dnsZoneFile: str
    memberTenantId: Optional[str] = None
    directoryId: Optional[str] = None
    catchAllAddress: Optional[str] = None
    subAddressing: SubAddressing | SubAddressingCustom
    allowRelaying: bool
    reportAddressUri: Optional[str] = None


class Credential(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class PasswordCredential(Credential):
    secret: str
    otpAuth: Optional[str] = None
    expiresAt: Optional[datetime] = None
    allowedIps: Optional[dict] = None


class SecondaryCredential(Credential):
    description: str
    secret: str
    createdAt: Optional[datetime] = None
    permissions: StalwartType
    allowedIps: Optional[dict] = None


class EmailAlias(BaseModel):
    enabled: bool
    name: str
    domainId: str
    description: Optional[str] = None


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

    class Types(StrEnum):
        USER = 'User'
        GROUP = 'Group'

    name: str
    domainId: Optional[str | dict] = None
    emailAddress: Optional[str] = None
    credentials: Optional[dict[str, PasswordCredential | SecondaryCredential]] = None
    createdAt: Optional[datetime] = None
    memberGroupsIds: Optional[dict] = None
    memberTenantId: Optional[str] = None
    roles: StalwartType | dict
    permissions: StalwartType
    quotas: Optional[dict] = None
    usedDiskQuota: Optional[int] = None
    aliases: Optional[dict[str, EmailAlias]] = None
    description: Optional[str] = None
    locale: Optional[str] = 'en_US'
    timezone: Optional[str] = None
    encryptionAtRest: StalwartType

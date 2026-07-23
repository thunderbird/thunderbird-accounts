from thunderbird_accounts.mail.types.jmap import BaseSchema
from enum import StrEnum
from typing import Optional, Annotated
from datetime import datetime
from pydantic import Field, ConfigDict, AliasChoices

Duration = Annotated[str | int, Field()]
"""A field that takes in either ms as an integer or time followed by the unit as a string
Ref: https://stalw.art/docs/0.15/configuration/values/duration"""


class StalwartType(BaseSchema):
    """Stalwart uses custom types in the shape of {'@type': 'Type'} (like {'@type': 'Enabled'}
    in Domain.subAddressing's case)

    This is a shape to ingest that, but we don't do any processing on what what might be inside."""

    model_config = ConfigDict(serialize_by_alias=True)
    type: Optional[str] = Field(
        validation_alias=AliasChoices('@type', 'type'), serialization_alias='@type', default=None
    )


class JMapType(BaseSchema):
    """Base type for all jmap responses"""

    id: Optional[str] = None


class DnsServer(StalwartType):
    """I'm not writing out all of the types, please reference:
    https://stalw.art/docs/ref/object/dns-server/
    """

    model_config = ConfigDict(polymorphic_serialization=True)

    host: str
    port: int = 53
    key_name: str
    key: str
    protocol: str
    tsig_algorithm: str
    description: str
    member_tenant_id: Optional[str] = None
    timeout: Duration
    ttl: Duration
    polling_interval: Duration
    propagation_timeout: Duration
    propagation_delay: Optional[Duration] = None


class DkimManagement(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class DkimManagementProperties(DkimManagement):
    """@type = Automatic
    Ref: https://stalw.art/docs/ref/object/domain/#dkimmanagementproperties"""

    algorithms: dict[str, bool]
    selector_template: str
    rotate_after: Duration
    retire_after: Duration
    delete_after: Duration


class DnsManagement(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class DnsManagementProperties(DnsManagement):
    dns_server_id: str
    origin: Optional[str] = None
    publish_records: dict


class SubAddressing(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class SubAddressingCustom(StalwartType):
    custom_role: dict


class Domain(JMapType):
    """Stalwart Domain Type

    Ref: https://stalw.art/docs/ref/object/domain/"""

    name: str
    aliases: dict  # list[str]
    is_enabled: bool
    created_at: datetime
    description: Optional[str] = None
    logo: Optional[str] = None
    certificate_management: dict | StalwartType
    dkim_management: DkimManagement | DkimManagementProperties
    dns_management: DnsManagement | DnsManagementProperties
    dns_zone_file: str
    member_tenant_id: Optional[str] = None
    directory_id: Optional[str] = None
    catch_all_address: Optional[str] = None
    sub_addressing: SubAddressing | SubAddressingCustom
    allow_relaying: bool
    report_address_uri: Optional[str] = None


class Credential(StalwartType):
    model_config = ConfigDict(polymorphic_serialization=True)


class PasswordCredential(Credential):
    secret: str
    otpAuth: Optional[str] = None
    expires_at: Optional[datetime] = None
    allowed_ips: Optional[dict] = None


class SecondaryCredential(Credential):
    description: str
    secret: str
    created_at: Optional[datetime] = None
    permissions: StalwartType
    allowed_ips: Optional[dict] = None


class EmailAlias(BaseSchema):
    enabled: bool
    name: str
    domain_id: str
    description: Optional[str] = None


class Account(JMapType, StalwartType):
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
    domain_id: Optional[str | dict] = None
    email_address: Optional[str] = None
    credentials: Optional[dict[str, PasswordCredential | SecondaryCredential]] = None
    created_at: Optional[datetime] = None
    member_groups_ids: Optional[dict] = None
    member_tenant_id: Optional[str] = None
    roles: StalwartType | dict
    permissions: StalwartType
    quotas: Optional[dict] = None
    used_disk_quota: Optional[int] = None
    aliases: Optional[dict[str, EmailAlias]] = None
    description: Optional[str] = None
    locale: Optional[str] = 'en_US'
    timezone: Optional[str] = None
    encryption_at_rest: StalwartType

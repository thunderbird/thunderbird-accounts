# =====================================================================================
# Stalwart v0.16 registry object types
# -------------------------------------------------------------------------------------
# Typed pydantic models for the Stalwart JMAP registry objects (Account / Domain /
# EmailAlias / Credential / DKIM management / quotas). Adapted from PR #1131.
#
# These are used INTERNALLY for non-fatal parsing/validation (schema-drift detection);
# the JMAP client always returns the v0.15-compatible dict at the caller boundary, so
# these models never replace the raw dict a caller receives.
# =====================================================================================

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

Duration = str | int
"""Either milliseconds as an int, or a value+unit string.
Ref: https://stalw.art/docs/0.15/configuration/values/duration"""


class StalwartType(BaseModel):
    """Stalwart tags typed objects with an ``@type`` discriminator (e.g.
    ``{'@type': 'Enabled'}``). This captures that discriminator without asserting the
    inner shape. ``extra='allow'`` so unknown sibling keys never fail validation."""

    model_config = ConfigDict(serialize_by_alias=True, extra='allow')
    type: Optional[str] = Field(
        validation_alias=AliasChoices('@type', 'type'), serialization_alias='@type', default=None
    )


class JMapType(BaseModel):
    """Base type for all JMAP registry objects."""

    model_config = ConfigDict(extra='allow')
    id: Optional[str] = None


class DkimManagement(StalwartType):
    pass


class DkimManagementProperties(DkimManagement):
    """@type = Automatic
    Ref: https://stalw.art/docs/ref/object/domain/#dkimmanagementproperties"""

    algorithms: Optional[dict[str, bool]] = None
    selectorTemplate: Optional[str] = None
    rotateAfter: Optional[Duration] = None
    retireAfter: Optional[Duration] = None
    deleteAfter: Optional[Duration] = None


class DnsManagement(StalwartType):
    pass


class DnsManagementProperties(DnsManagement):
    dnsServerId: Optional[str] = None
    origin: Optional[str] = None
    publishRecords: Optional[dict] = None


class SubAddressing(StalwartType):
    pass


class DomainType(JMapType):
    """Stalwart Domain object.

    Ref: https://stalw.art/docs/ref/object/domain/
    """

    name: str
    aliases: Optional[dict] = None
    isEnabled: Optional[bool] = None
    createdAt: Optional[datetime] = None
    description: Optional[str] = None
    logo: Optional[str] = None
    certificateManagement: Optional[dict | StalwartType] = None
    dkimManagement: Optional[DkimManagement | DkimManagementProperties | dict] = None
    dnsManagement: Optional[DnsManagement | DnsManagementProperties | dict] = None
    dnsZoneFile: Optional[str] = None
    memberTenantId: Optional[str] = None
    directoryId: Optional[str] = None
    catchAllAddress: Optional[str] = None
    subAddressing: Optional[SubAddressing | dict] = None
    allowRelaying: Optional[bool] = None
    reportAddressUri: Optional[str] = None


class Credential(StalwartType):
    pass


class PasswordCredential(Credential):
    secret: Optional[str] = None
    credentialId: Optional[str] = None
    otpAuth: Optional[str] = None
    expiresAt: Optional[datetime] = None
    allowedIps: Optional[dict] = None


class SecondaryCredential(Credential):
    description: Optional[str] = None
    secret: Optional[str] = None
    credentialId: Optional[str] = None
    createdAt: Optional[datetime] = None
    permissions: Optional[StalwartType | dict] = None
    allowedIps: Optional[dict] = None


class EmailAlias(BaseModel):
    """A single alias entry in the account ``aliases`` VecMap.

    ``name`` is the email LOCAL PART (a full email is rejected by Stalwart), paired with
    a resolved ``domainId``.
    """

    model_config = ConfigDict(serialize_by_alias=True, extra='allow')
    type: Optional[str] = Field(
        validation_alias=AliasChoices('@type', 'type'), serialization_alias='@type', default='EmailAlias'
    )
    enabled: bool = True
    name: str
    domainId: Optional[str] = None
    description: Optional[str] = None


class AccountType(JMapType):
    """Stalwart Account object.

    Ref: https://stalw.art/docs/ref/object/account/
    """

    class Types(StrEnum):
        USER = 'User'
        GROUP = 'Group'

    type: Optional[str] = Field(
        validation_alias=AliasChoices('@type', 'type'), serialization_alias='@type', default=None
    )
    name: str
    domainId: Optional[str] = None
    emailAddress: Optional[str] = None
    credentials: Optional[dict[str, PasswordCredential | SecondaryCredential | dict]] = None
    createdAt: Optional[datetime] = None
    memberGroupIds: Optional[dict] = None
    memberTenantId: Optional[str] = None
    roles: Optional[StalwartType | dict] = None
    permissions: Optional[StalwartType | dict] = None
    quotas: Optional[dict] = None
    usedDiskQuota: Optional[int] = None
    aliases: Optional[dict[str, EmailAlias]] = None
    description: Optional[str] = None
    locale: Optional[str] = 'en_US'
    timeZone: Optional[str] = None
    encryptionAtRest: Optional[StalwartType | dict] = None

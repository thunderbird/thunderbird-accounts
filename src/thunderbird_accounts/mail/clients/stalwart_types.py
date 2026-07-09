from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class StalwartType(BaseModel):
    """Stalwart uses custom types in the shape of {'@type': 'Type'} (like {'@type': 'Enabled'} 
    in Domain.subAddressing's case)
    
    This is a shape to ingest that, but we don't do any processing on what what might be inside."""

    type: Optional[str] = Field(alias='@type', default=None)


class DomainType(BaseModel):
    """Stalwart Domain Type

    Ref: api_url_.
    .. api_doc: https://stalw.art/docs/ref/object/domain/"""
    id: str
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

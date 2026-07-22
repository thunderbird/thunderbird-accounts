# =====================================================================================
# JMAP protocol envelope types (RFC 8620)
# -------------------------------------------------------------------------------------
# Typed pydantic models for the JMAP request/response envelope + the Session Resource,
# used internally by the transport (`jmap_client.py`) for session discovery and typed
# request construction. Adapted from PR #1131 (the broken `from sqlparse.tokens import
# Literal` import is fixed to `typing.Literal`).
# =====================================================================================

from __future__ import annotations

import enum
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        populate_by_name=True,
        from_attributes=True,
    )


class ResponseIndex(enum.Enum):
    NAME = 0
    DATA = 1
    CALL_IDS = 2


class Invocation(BaseSchema):
    """A single JMAP method call.

    ``name`` is the method (e.g. ``x:Domain/get``), ``arguments`` is the request payload,
    and ``method_call_id`` is a client-chosen id used to reference this call in a batched
    request (via a ``#ids`` result reference).

    Ref: https://jmap.io/spec/rfc8620/#section-3.2
    """

    name: str
    arguments: dict
    method_call_id: str

    @model_validator(mode='before')
    @classmethod
    def transform_tuple(cls, data):
        """The wire format is a 3-tuple; accept it and map back onto our fields."""
        if isinstance(data, list):
            data = {'name': data[0], 'arguments': data[1], 'method_call_id': data[2]}
        return data

    @model_serializer(mode='plain')
    def serialize_model(self) -> list:
        """The JMAP spec wants each method call serialized as a 3-element list."""
        return [self.name, self.arguments, self.method_call_id]


class JMapRequest(BaseSchema):
    using: list[str]
    method_calls: list[Invocation]
    created_ids: Optional[list[str]] = Field(default=None)


class JMapResponse(BaseSchema):
    method_responses: list[Invocation] = Field()
    created_ids: Optional[list[str]] = Field(default=None)
    session_state: str = Field()


class JMapCorePropertyCapability(TypedDict):
    maxSizeUpload: int
    maxConcurrentUpload: int
    maxSizeRequest: int
    maxConcurrentRequests: int
    maxCallsInRequest: int
    maxObjectsInGet: int
    maxObjectsInSet: int
    collationAlgorithms: list[str]


class AccountType(TypedDict, total=False):
    name: str
    isPersonal: bool
    isReadOnly: bool
    accountCapabilities: dict


class SessionResource(TypedDict):
    capabilities: dict | dict[Literal['urn:ietf:params:jmap:core'], JMapCorePropertyCapability]
    accounts: dict[str, AccountType]
    primaryAccounts: dict[str, str]
    username: str
    apiUrl: str
    downloadUrl: str
    uploadUrl: str
    eventSourceUrl: str
    state: str

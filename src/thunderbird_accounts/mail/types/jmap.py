import enum
from typing import Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator
from pydantic.alias_generators import to_camel
from sqlparse.tokens import Literal


class BaseSchema(BaseModel):
    """A base schema that allows us to ingest camelCase names to snake_case variables.
    This will serialize it back to camelCase for requests as well."""

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
    """The actual request to the jmap api.

    The ``name`` is the request you'd like to make (e.g. ``x:Domains/get`` to do a get request for Stalwart domains.)
    ``arguments`` is the request data, and ``method_call_id`` is an id that can be used to reference this request in batched queries.

    Ref: doc_url_.
    .. doc_url: https://jmap.io/spec/rfc8620/#section-3.2"""

    name: str
    arguments: dict
    method_call_id: str

    @model_validator(mode='before')
    @classmethod
    def transform_tuple(cls, data):
        """Since we serialize this model as a list, we need to a way to reverse this serialization."""
        if isinstance(data, list):
            data = {'name': data[0], 'arguments': data[1], 'method_call_id': data[2]}
        return data

    @model_serializer(mode='plain')
    def serialize_model(self) -> list:
        """JMAP spec wants this data as a tuple (well list in our case.)"""
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

import enum
from typing import NamedTuple, TypedDict, NotRequired
from sqlparse.tokens import Literal

class ResponseIndex(enum.Enum):
    NAME = 0
    DATA = 1
    CALL_IDS = 2

class Invocation(NamedTuple):
    name: str
    arguments: dict #dict[str, str]
    methodCallId: str


class JMapRequest(TypedDict):
    using: list[str]
    methodCalls: list[Invocation]
    createdIds: NotRequired[list[str]]


class JMapResponse(TypedDict):
    methodResponses: list[Invocation]
    createdIds: NotRequired[list[str]]
    sessionState: str


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

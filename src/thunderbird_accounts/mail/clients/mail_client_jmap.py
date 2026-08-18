"""JMap Stalwart client

This file contains 3 classes:
    - ``BaseJMAP``: which hosts some common classes, as well as some class level variables.
    - ``MailClientUserJMAP``: which is derived from BaseJMAP, and hosts the app password functionality. This requires
a user jwt since the interface for creating stalwart credentials aren't available from the admin api.
    - ``MailClientAdminJMAP``: also derived from BaseJMAP. This hosts basically everything else, and is almost a
clone of mail_client_interface/legacy. The main difference is some return types are pydantic'd, and some functions
were marked with a starting ``_`` to indicate they're not used outside of this class.

"""

import logging
import uuid
from abc import ABC
from typing import Optional, Type

import requests
import sentry_sdk
from cryptography.hazmat.primitives import _serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from dns import rdatatype, zone
from pydantic import BaseModel, ValidationError

from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.clients.mail_client_interface import (
    DkimSignatureStage,
    MailClientInterface,
    DNSRecordStatus,
    DomainVerificationErrors,
)
from thunderbird_accounts.mail.dns import enrich_dns_records_with_status
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
    AccountSetError,
    AppPasswordSetError,
    DomainAlreadyExistsError,
    DomainNotFoundError,
    DomainSetError,
    FailedToCreateDKIM,
    InvalidJMapResponseError,
    JMapError,
)
from thunderbird_accounts.mail.types import jmap, stalwart
from thunderbird_accounts.mail.types.jmap import Invocation, JMapRequest
from thunderbird_accounts.mail.types.stalwart import AppPassword, StalwartMethods, StalwartType


class BaseJMAP(ABC):
    client: JMAPClient
    account_id: Optional[str] = None
    primary_domain_id: Optional[str] = None

    def _get_user_client(
        self, username, user_token, auth_type: JMAPClient.AUTH_TYPES = JMAPClient.AUTH_TYPES.BEARER
    ) -> JMAPClient:
        client = JMAPClient(settings.STALWART_JMAP_API_URL, username, user_token, auth_type)
        # Make sure we retrieve the session
        client.get_session()
        return client

    def _get_session(self):
        session = self.client.get_session()

        # Retrieve our account from the primary account for jmap calls
        self.account_id = session.primary_accounts.get('urn:stalwart:jmap')
        if not self.account_id:
            self.account_id = list(session.accounts.keys())[0]

    def _get_primary_domain_id(self):
        """We cache the primary domain id at the moment to avoid having to retrieve it many times over.
        This runs during preflight check so we don't need to call it in here."""
        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.query(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'filter': {'name': settings.PRIMARY_EMAIL_DOMAIN},
                            'limit': 1,
                            'position': 0,
                            'calculateTotal': False,
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        id_list = response.method_responses[0].arguments.get('ids', [])

        if len(id_list) == 0:
            return

        self.primary_domain_id = id_list[0]

    def _handle_jmap_error(self, error_obj: dict, error: Type[JMapError]) -> JMapError:
        """Pass it the error object, and it will set and return your exception"""
        error_type = error_obj.get('type')
        error_reason = error_obj.get('description')
        error_fields = error_obj.get('properties')
        return error(error_type, error_reason, error_fields)

    def preflight_check(self):
        if not self.account_id:
            self._get_session()
        if not self.primary_domain_id:
            self._get_primary_domain_id()

    def _debug_dump(self, name: str, data: dict):
        pass
        #with open(f'd_{name}.json', 'w') as fh:
        #    fh.write(json.dumps(data, indent=2))

    def _query_account_by_principal_id(self, principal_id: str, method_call_id: str = '0') -> Invocation:
        """Helper to return an Invocation object that will query the account by local part / primary domain id
        Optionally you can provide a custom method_call_id to reference in future Invocations.

        If method_call_id is left to the default value you can reference the id with:

        .. code-block:: python

        {'resultOf': '0', 'name': 'x:Account/query', 'path': '/ids'}

        """
        account_name = principal_id.split('@')[0]
        return Invocation(
            name=StalwartMethods.query(StalwartMethods.ACCOUNT),
            arguments={
                'accountId': self.account_id,
                'filter': {'name': account_name, 'domainId': self.primary_domain_id},
                'limit': 5,
                'position': 0,
                'calculateTotal': True,
            },
            method_call_id=method_call_id,
        )


class MailClientUserJMAP(BaseJMAP):
    """Some api endpoints are only accessible via the user's own token.
    We've split this out to a separate object to avoid conflating admin scoped functions with user scoped functions"""

    class SaveAppPasswordReturn(BaseModel):
        id: str
        secret: str

    def __init__(self, username, user_jwt: str):
        self.client = self._get_user_client(username, user_jwt, JMAPClient.AUTH_TYPES.BEARER)
        self.account_id = None
        self.primary_domain_id = None

    def get_identity(self) -> list[jmap.Identity]:
        """Retrieves and returns a list of jmap identities (display name, email, signature)"""
        self.preflight_check()
        response = self.client.request(
            JMapRequest(
                using=['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:submission'],
                method_calls=[
                    Invocation(
                        name='Identity/get',
                        arguments={
                            'accountId': self.account_id,
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )
        self._debug_dump('get_identity', response.method_responses[0].arguments)

        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise RuntimeError('No identities found')

        identities = response.method_responses[0].arguments.get('list', [])

        try:
            return [jmap.Identity(**identity) for identity in identities]
        except ValidationError as ex:
            logging.warning('[MailClientUserJMAP.get_identity]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex) from ex

    def save_app_password(self, label: str) -> SaveAppPasswordReturn:
        """Create an app password with a given label and return the pkid and secret the server generates."""
        self.preflight_check()

        credentials = AppPassword(
            description=label,
            permissions=StalwartType(type='Inherit'),
            allowed_ips={},
        )

        temp_id = str(uuid.uuid4())
        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.set(StalwartMethods.APP_PASSWORD),
                        arguments={
                            'accountId': self.account_id,
                            'create': {
                                temp_id: {
                                    **credentials.model_dump(exclude_unset=True),
                                }
                            },
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        self._debug_dump('set_app_password', response.method_responses[0].arguments)

        data = response.method_responses[0].arguments.get('created', {}).get(temp_id, {})

        return self.SaveAppPasswordReturn(id=data.get('id'), secret=data.get('secret'))

    def delete_app_password(self, app_password_pkid: str):
        """Removes an app password by the pkid."""
        self.preflight_check()

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.destroy(StalwartMethods.APP_PASSWORD),
                        arguments={'accountId': self.account_id, 'destroy': [app_password_pkid]},
                        method_call_id='0',
                    ),
                ],
            )
        )

        self._debug_dump('delete_app_password', response.method_responses[0].arguments)

        # Error during deletion
        data = response.method_responses[0].arguments.get('destroyed', [])
        error = response.method_responses[0].arguments.get('notDestroyed')
        if error:
            error_obj = list(error.values())[0]
            raise self._handle_jmap_error(error_obj, AppPasswordSetError)
        elif len(data) == 0:
            raise ValueError('Response has no pkid!')

        return data[0] == app_password_pkid


class MailClientAdminJMAP(MailClientInterface, BaseJMAP):
    """The JMap client for communication with Stalwart's Admin api.

    This class is nearly identical to ``mail_client_legacy`` which hosts the old pre-v0.16 api client. Some functions
    are return typed with pydantic types, and some functions are prefixed with ``_`` if they're not used outside of
    this class.

    Ideally this class will:
        - Return pydantic types for ``Get`` functions.
        - Return pkid (or list of pkids) for ``Create`` functions.
        - Return nothing for ``Update`` or ``Delete`` functions.

    Any errors should raise an appropriate custom exception type so they can be clearly caught.

    For easier navigation some sections have been marked such as ``# Section Name``.

    These sections are:
        - Domain
        - Account
        - Alias / Email Address
        - DKIM
        - DNS
    """

    def __init__(self):
        # FIXME: Setup correct admin login
        self.client = self._get_user_client(
            settings.STALWART_JMAP_API_AUTH_USER,
            settings.STALWART_JMAP_API_AUTH_SECRET,
            JMAPClient.AUTH_TYPES.BASIC
            if settings.STALWART_JMAP_API_AUTH_METHOD == 'basic'
            else JMAPClient.AUTH_TYPES.BEARER,
        )
        self.account_id = None
        self.primary_domain_id = None

    def _get_domain_ids_by_name(self, emails: list[str]) -> dict[str, str]:
        """Return a dictionary keyed by domain name pointing to their domain id."""
        # Sort aliases by domain
        alias_domains = {}
        for email in emails:
            if '@' not in email:
                continue

            _, alias_domain = email.split('@')
            if not alias_domains.get(alias_domain):
                alias_domains[alias_domain] = [email]
                continue

            alias_domains[alias_domain].append(email)

        # Build our domain id query list
        domain_names = []
        if len(alias_domains):
            domain_names += [alias_domain for alias_domain in alias_domains.keys()]

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    # x:Domain/query does not support OR filter,
                    # so we have to do a separate request for each domain
                    Invocation(
                        name=StalwartMethods.query(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'filter': {'name': domain_name},
                            'limit': 5,
                            'position': 0,
                            'calculateTotal': False,
                        },
                        method_call_id=str(idx),
                    )
                    for idx, domain_name in enumerate(domain_names)
                ],
            )
        )

        domain_ids_by_domain = {}

        debug_dump = []
        for idx, _r in enumerate(response.method_responses):
            debug_dump.append(_r.arguments)
            id_list = _r.arguments.get('ids', [])
            domain_name = domain_names[idx]
            # Previously examples have required a domain to exist before we attach it to an account
            if len(id_list) == 0:
                raise DomainNotFoundError(domain_name)
            domain_ids_by_domain[domain_name] = id_list[0]

        self._debug_dump('set_account-domain_query', {'_': debug_dump})

        return domain_ids_by_domain

    def _handle_destroy(self, method: StalwartMethods, pkid: str | list[str]) -> None:
        """Generic JMap destroy command, pass in your Stalwart method and a list of pkids."""
        if isinstance(pkid, str):
            pkid = [pkid]

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.destroy(method),
                        arguments={
                            'accountId': self.account_id,
                            'destroy': pkid,
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        self._debug_dump(f'{method.replace("/", "_")}_handle_destroy', response.method_responses[0].arguments)

        error = response.method_responses[0].arguments.get('notDestroyed')
        if not error:
            return

        error_obj = list(error.values())[0]
        raise self._handle_jmap_error(error_obj, DomainSetError)

    #
    # Domain
    #

    def _get_domains_by_id(self, domain_ids: str | list[str]) -> list[stalwart.Domain]:
        self.preflight_check()

        if isinstance(domain_ids, str):
            domain_ids = [domain_ids]

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.get(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'ids': domain_ids,
                        },
                        method_call_id='1',
                    ),
                ],
            )
        )

        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise DomainNotFoundError(domain_ids[0])

        data = response.method_responses[0].arguments.get('list', [])
        self._debug_dump('_get_domains_by_id', response.method_responses[0].arguments)

        try:
            return [stalwart.Domain(**domain) for domain in data]
        except ValidationError as ex:
            logging.warning(f'[MailClient._get_domains_by_id({domain_ids}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex) from ex

    def get_domain(self, domain: str) -> stalwart.Domain:
        """Retrieve a :any thunderbird_accounts.mail.types.stalwart.Domain:
        object from a given domain name.

        :raises DomainNotFoundError: If the domain is not found within Stalwart.
        :raises InvalidJMapResponseError: If the response from Stalwart presents a malformed Domain object."""
        self.preflight_check()

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.query(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'filter': {'name': domain},
                            'limit': 25,
                            'position': 0,
                            'calculateTotal': True,
                        },
                        method_call_id='0',
                    ),
                    Invocation(
                        name=StalwartMethods.get(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            '#ids': {'resultOf': '0', 'name': 'x:Domain/query', 'path': '/ids'},
                        },
                        method_call_id='1',
                    ),
                ],
            )
        )

        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise DomainNotFoundError(domain)

        data = response.method_responses[1].arguments.get('list', [])[0]
        self._debug_dump('get_domain', response.method_responses[1].arguments)

        try:
            return stalwart.Domain(**data)
        except ValidationError as ex:
            logging.warning(f'[MailClient.get_domain({domain}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex) from ex

    def create_domain(self, domain, description='', **kwargs) -> jmap.Id:
        self.preflight_check()

        # Compat
        is_enabled = kwargs.get('is_enabled', True)

        # If description is an empty string make it none
        if not description.strip():
            description = None

        # If the domain already exists, we ignore and return None
        try:
            self.get_domain(domain)
            raise DomainAlreadyExistsError(domain)
        except DomainNotFoundError:
            pass

        domain = stalwart.DomainCreate(
            name=domain,
            is_enabled=is_enabled,
            description=description,
            aliases={},
            certificate_management=stalwart.StalwartType(type='Manual'),
            dkim_management=stalwart.StalwartType(type='Manual'),
            dns_management=stalwart.StalwartType(type='Manual'),
            sub_addressing=stalwart.StalwartType(type='Enabled'),
        )

        temp_id = str(uuid.uuid4())
        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.set(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'create': {temp_id: domain.model_dump(exclude_unset=True)},
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        self._debug_dump('create_domain', response.method_responses[0].arguments)

        error = response.method_responses[0].arguments.get('notCreated')
        if error:
            error_obj = error.get(temp_id, {})
            raise self._handle_jmap_error(error_obj, DomainSetError)

        data = response.method_responses[0].arguments.get('created', {})

        stalwart_pkid = data.get(temp_id, {}).get('id')

        # Just in case the account was not created and Stalwart missed an error check
        if not stalwart_pkid:
            raise DomainNotFoundError(domain)

        # Return the pkid
        return stalwart_pkid

    def update_domain(self, domain_name: str, data: stalwart.DomainUpdate):
        domain = self.get_domain(domain_name)
        if not domain.id:
            raise DomainNotFoundError(domain_name)

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.set(StalwartMethods.DOMAIN),
                        arguments={
                            'accountId': self.account_id,
                            'update': {
                                domain.id: {
                                    **data.model_dump(exclude_unset=True),
                                }
                            },
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        data = response.method_responses[0].arguments.get('updated', {})
        self._debug_dump('update_domain', data)

        # I've never seen this return anything useful tbh, but we'll return a generic dict for now.
        return data

    def delete_domain(self, domain_name: str) -> None:

        # Allow DomainNotFound to raise if the domain is not found
        domain = self.get_domain(domain_name)
        if not domain.id:
            raise DomainNotFoundError(domain_name)

        self.delete_dkim(domain_name)
        self._handle_destroy(StalwartMethods.DOMAIN, domain.id)

    #
    # Account
    #

    def get_account(self, principal_id: str) -> stalwart.Account:
        """Retrieve an :any thunderbird_accounts.mail.types.stalwart.Account: from a given
        primary thundermail address.

        :raises AccountNotFoundError: If the account is not found within Stalwart.
        :raises InvalidJMapResponseError: If the response from Stalwart presents a malformed AccountType object."""
        self.preflight_check()

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    self._query_account_by_principal_id(principal_id),
                    Invocation(
                        name=StalwartMethods.get(StalwartMethods.ACCOUNT),
                        arguments={
                            'accountId': self.account_id,
                            '#ids': {'resultOf': '0', 'name': 'x:Account/query', 'path': '/ids'},
                        },
                        method_call_id='1',
                    ),
                ],
            )
        )

        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise AccountNotFoundError(principal_id)

        data = response.method_responses[1].arguments.get('list', [])[0]
        self._debug_dump('get_account', response.method_responses[1].arguments)

        if len(data.get('aliases', {}).values()) > 0:
            domain_ids = [alias.get('domainId') for alias in data.get('aliases', {}).values()]
            domains = self._get_domains_by_id(domain_ids)
            # FIXME: We should just require domains to have their new stalwart ids...
            for idx, domain in data.get('aliases').items():
                data['aliases'][idx]['full_address'] = f'{domain.get("name")}@{domains[0].name}'

        try:
            return stalwart.Account(**data)
        except ValidationError as ex:
            logging.warning(f'[MailClient.get_account({principal_id}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex)

    def create_account(
        self,
        emails: list[str],
        principal_id: str,
        full_name: Optional[str] = None,
        app_password: Optional[str] = None,
        quota: Optional[int] = None,
    ) -> jmap.Id:
        """Creates a Stalwart Account object from the given values. Domains for aliases need to be created
        ahead of time.

        Note: App password is deprecated, it's not used within actual working code and so we'll remove it soon.

        :raises RuntimeError: If app_password is any value except for None.
        :raises DomainNotFoundError: If an email alias domain is not found within Stalwart.
        :raises AccountSetError: If there was an error with Stalwart or one of our parameters in the request.
        :raises AccountNotFoundError: If somehow the account was created but no id was returned."""
        self.preflight_check()

        if app_password:
            raise RuntimeError('app_password is a deprecated property and cannot be used.')

        account_name, account_domain = principal_id.split('@')

        domain_ids_by_domain = self._get_domain_ids_by_name([principal_id, *emails])

        aliases = {
            str(idx): stalwart.EmailAlias(
                enabled=True, name=email.split('@')[0], domain_id=domain_ids_by_domain[email.split('@')[1]]
            )
            for idx, email in enumerate(emails)
        }
        data = stalwart.Account(
            type=stalwart.Account.Types.USER.value,
            name=account_name,
            description=full_name,
            encryption_at_rest=stalwart.StalwartType(type='Disabled'),
            roles=stalwart.StalwartType(type='User'),
            permissions=stalwart.StalwartType(type='Inherit'),
            domain_id=domain_ids_by_domain[account_domain],
            aliases=aliases,
            quotas=stalwart.StorageQuota(max_disk_quota=quota) if quota else None,
        )

        temp_id = str(uuid.uuid4())
        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.set(StalwartMethods.ACCOUNT),
                        arguments={
                            'accountId': self.account_id,
                            'create': {
                                temp_id: {
                                    **data.model_dump(exclude_unset=True),
                                }
                            },
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        error = response.method_responses[0].arguments.get('notCreated')
        if error:
            error_obj = error.get(temp_id, {})
            raise self._handle_jmap_error(error_obj, AccountSetError)

        data = response.method_responses[0].arguments.get('created', {})
        self._debug_dump('set_account', response.method_responses[0].arguments)

        stalwart_pkid = data.get(temp_id, {}).get('id')

        # Just in case the account was not created and Stalwart missed an error check
        if not stalwart_pkid:
            raise AccountNotFoundError(principal_id)

        return stalwart_pkid

    def update_account(self, principal_id: str, data: stalwart.AccountUpdate) -> dict:
        """"""
        self.preflight_check()

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[self._query_account_by_principal_id(principal_id)],
            )
        )

        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise AccountNotFoundError(principal_id)

        stalwart_pkid = response.method_responses[0].arguments.get('ids', [])[0]

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.set(StalwartMethods.ACCOUNT),
                        arguments={
                            'accountId': self.account_id,
                            'update': {
                                stalwart_pkid: {
                                    **data.model_dump(exclude_unset=True),
                                }
                            },
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        data = response.method_responses[0].arguments.get('updated', {})
        self._debug_dump('patch_account', data)

        # I've never seen this return anything useful tbh, but we'll return a generic dict for now.
        return data

    def delete_account(self, principal_id: str) -> None:
        """
        Deletes a Stalwart account from the given thundermail address.

        :raises AccountNotFoundError: If the account you're trying to delete does not exist.
        :raises AccountSetError: If there was a problem during the deletion process."""
        self.preflight_check()

        account = self.get_account(principal_id)
        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.destroy(StalwartMethods.ACCOUNT),
                        arguments={
                            'accountId': self.account_id,
                            'destroy': [account.id],
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        # Error during deletion
        error = response.method_responses[0].arguments.get('notDestroyed')
        if error:
            error_obj = list(error.values())[0]
            raise self._handle_jmap_error(error_obj, AccountSetError)

        data = response.method_responses[0].arguments.get('destroyed', {})
        self._debug_dump('delete_account', data)

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> None:
        """Updates Stalwart and changes their primary email address and/or full name"""

        account = stalwart.AccountUpdate(name=primary_email_address or None, description=full_name or None)

        if not account.name and not account.description:
            raise ValueError('You must provide at least one field to change.')

        self.update_account(principal_id, account)

    def update_quota(self, principal_id: str, quota: int) -> None:
        account = stalwart.AccountUpdate(quotas=stalwart.StorageQuota(max_disk_quota=quota))
        self.update_account(principal_id, account)

    #
    # Alias / Email Address
    #

    def save_email_addresses(self, principal_id: str, emails: str | list[str]) -> None:
        """Saves a list of new aliases to Stalwart.
        We need to first look-up the existing stalwart account to get a fresh list of aliases,
        then we retrieve domain ids to apply domains.

        FIXME: This does not check for dupes yet."""
        if isinstance(emails, str):
            emails = [emails]

        if len(emails) == 0:
            return

        # Retrieve a fresh list of our aliases
        account = self.get_account(principal_id)

        domain_ids_by_name = self._get_domain_ids_by_name(emails)

        first_id = 0
        if account.aliases:
            first_id = int(list(account.aliases.keys())[-1]) + 1

        # We're forming json pointer paths here, in this case `aliases/0: { ... data to update ... }`
        # if we pass the entire "list" it will simply replace everything.
        aliases = {
            f'aliases/{first_id + idx}': stalwart.EmailAlias(
                name=alias.split('@')[0], domain_id=domain_ids_by_name[alias.split('@')[1]], enabled=True
            )
            for idx, alias in enumerate(emails)
        }
        account_update = stalwart.AccountUpdate(**aliases)  # ty: ignore[invalid-argument-type]
        self.update_account(principal_id, account_update)

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]) -> None:
        """Previously we replaced email addresses. That's fine,
        but for now let's just delete the old and add in the new."""
        to_remove, to_add = zip(*emails)
        self.delete_email_addresses(principal_id, list(to_remove))
        self.save_email_addresses(principal_id, list(to_add))

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]) -> None:
        if isinstance(emails, str):
            emails = [emails]

        if len(emails) == 0:
            return

        # Retrieve a fresh list of our aliases
        account = self.get_account(principal_id)
        domain_ids_by_name = self._get_domain_ids_by_name(emails)

        if not account.aliases:
            return  # EmailNotFound

        # Gross double loop to find a match between saved aliases, and aliases to remove / domain_ids
        ids_to_remove = []
        for idx, alias in account.aliases.items():
            for email in emails:
                local_part, domain_name = email.split('@')
                domain_id = domain_ids_by_name.get(domain_name)
                if not domain_id:
                    continue
                if alias.name == local_part and alias.domain_id == domain_id:
                    ids_to_remove.append(idx)

        # None out the aliases in question
        aliases = {f'aliases/{idx}': None for idx in ids_to_remove}
        account_update = stalwart.AccountUpdate(**aliases)
        self.update_account(principal_id, account_update)

    #
    # DKIM
    #

    def _get_dkim_dns_records(self, domain_name: str) -> list[stalwart.DnsRecord]:
        return [
            record
            for record in self._get_dns_records(domain_name)
            if record.type == 'TXT' and '_domainkey' in (record.name or '')
        ]

    def _get_dkim_selectors(self, domain_name: str) -> set[str]:
        """Return DKIM selectors already present in Stalwart's DNS records."""
        selectors = set()
        domain_name = domain_name.rstrip('.').lower()
        suffix = f'._domainkey.{domain_name}'

        for record in self._get_dkim_dns_records(domain_name):
            if record.type != 'TXT':
                continue

            record_name = (record.name or '').rstrip('.').lower()
            if not record_name.endswith(suffix):
                continue

            selector = record_name[: -len(suffix)]
            if selector:
                selectors.add(selector)

        return selectors

    def create_dkim(self, domain, stage: DkimSignatureStage = DkimSignatureStage.PENDING, algorithms=None):
        """Creates either a ed25519 or rsa dkim signature including private key that is submitted to Stalwart.

        FIXME: This function can be optimized to do both creations in one request, but for now it's split up."""
        dkim_algorithms = settings.STALWART_DKIM_ALGOS if algorithms is None else algorithms

        try:
            domain_obj = self.get_domain(domain)
        except DomainNotFoundError:
            raise

        pkid_list = []
        responses = []
        for algorithm in dkim_algorithms:
            selector = settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm)

            # cryptography's types are not really compatible with each other,
            # but they overlap enough for this to work.
            if algorithm == 'Ed25519':
                dkim_type = stalwart.DkimSignature.Types.DKIM1_Ed25519_SHA_256
                private_key = Ed25519PrivateKey.generate()
            elif algorithm == 'Rsa':
                dkim_type = stalwart.DkimSignature.Types.DKIM1_RSA_SHA_256
                private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            else:
                logging.warning(f'Unknown algorithm {algorithm}. DkimSignature creation is being skipped.')
                continue

            signature = stalwart.DkimSignature1(
                type=dkim_type.value,
                selector=selector,
                domain_id=domain_obj.id,
                stage=stage.value,
                private_key=stalwart.SecretText(
                    type='Text',
                    secret=private_key.private_bytes(
                        encoding=_serialization.Encoding.PEM,
                        format=_serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=_serialization.NoEncryption(),
                    ),
                ),
            )

            temp_id = str(uuid.uuid4())
            try:
                response = self.client.request(
                    JMapRequest(
                        using=[
                            'urn:ietf:params:jmap:core',
                            'urn:stalwart:jmap',
                        ],
                        method_calls=[
                            Invocation(
                                name=StalwartMethods.set(StalwartMethods.DKIM_SIGNATURE),
                                arguments={
                                    'accountId': self.account_id,
                                    'create': {
                                        temp_id: {**signature.model_dump(exclude_unset=True)},
                                    },
                                },
                                method_call_id='0',
                            ),
                        ],
                    )
                )

                error = response.method_responses[0].arguments.get('notCreated')
                if error:
                    error_obj = error.get(temp_id, {})
                    raise self._handle_jmap_error(error_obj, DomainSetError)

                data = response.method_responses[0].arguments.get('created', {})

                stalwart_pkid = data.get(temp_id, {}).get('id')
                responses.append(data)
                if not stalwart_pkid:
                    raise FailedToCreateDKIM(algorithm, domain, 'pkid not found')
                pkid_list.append(stalwart_pkid)
            except requests.RequestException as exc:
                raise FailedToCreateDKIM(algorithm, domain, str(exc)) from exc

        self._debug_dump('create_dkim', {'_': responses})

        # Return the pkid
        return pkid_list

    def get_dkim_signatures(self, domain_name: str) -> list[stalwart.DkimSignature]:
        self.preflight_check()

        domain = self.get_domain(domain_name)

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name=StalwartMethods.query(StalwartMethods.DKIM_SIGNATURE),
                        arguments={
                            'accountId': self.account_id,
                            'filter': {'domainId': domain.id},
                            'limit': 25,
                            'position': 0,
                            'calculateTotal': True,
                        },
                        method_call_id='0',
                    ),
                    Invocation(
                        name=StalwartMethods.get(StalwartMethods.DKIM_SIGNATURE),
                        arguments={
                            'accountId': self.account_id,
                            '#ids': {'resultOf': '0', 'name': 'x:DkimSignature/query', 'path': '/ids'},
                        },
                        method_call_id='1',
                    ),
                ],
            )
        )

        self._debug_dump('get_dkim_signatures', response.method_responses[1].arguments)

        # FIXME: Temp
        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise RuntimeError(domain_name)

        dkim_signatures = response.method_responses[1].arguments.get('list', [])
        signatures = [stalwart.DkimSignature(**signature) for signature in dkim_signatures]

        return signatures

    def delete_dkim(self, domain):
        dkim_signatures = self.get_dkim_signatures(domain)
        dkim_signature_ids = [signature.id for signature in dkim_signatures]
        self._handle_destroy(StalwartMethods.DKIM_SIGNATURE, dkim_signature_ids)  # ty: ignore[invalid-argument-type]

    def ensure_dkim(self, domain_name: str, stage: DkimSignatureStage = DkimSignatureStage.PENDING):
        existing_selectors = self._get_dkim_selectors(domain_name)

        missing_algorithms = [
            algorithm
            for algorithm in settings.STALWART_DKIM_ALGOS
            if (settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm) or '').lower() not in existing_selectors
        ]

        if not missing_algorithms:
            return []

        return self.create_dkim(domain_name, stage=stage, algorithms=missing_algorithms)

    def activate_pending_dkim_signatures(self, domain_name: str) -> list[str]:
        """No-op, work out of scope."""
        return []

    #
    # DNS
    #

    def _get_dns_records(self, domain_name: str) -> list[stalwart.DnsRecord]:
        """Retrieve dns records for a particular domain.

        Previously we could fetch this nicely with a single endpoint that is already split up for us.
        Now we have to read/parse a zonefile via dnspython. I'm not 100% sure the end result will be the same."""
        domain = self.get_domain(domain_name)

        dns_records = []
        # Need to set a default ttl otherwise dnspython will yell at us
        dns_zone_str = f'$TTL 3600\n{domain.dns_zone_file}'

        # If we want to exclude the origin at some point in the future flip this to True.
        exclude_origin = False
        dns_zone_file = zone.from_text(
            dns_zone_str, origin=domain_name, relativize=exclude_origin, check_origin=False, allow_directives=True
        )
        for name, _ttl, rdata in dns_zone_file.iterate_rdatas():
            dns_records.append(
                stalwart.DnsRecord(type=rdatatype.to_text(rdata.rdtype), name=str(name), content=str(rdata))
            )

        return dns_records

    def build_expected_dns_records(self, cust_domain: str) -> list[dict]:
        """Build the full list of DNS records the user must configure for a customer domain.

        TODO: Remove this out of the api client.
        FIXME: Have this form and return DnsRecord"""
        from thunderbird_accounts.mail.dkim import build_customer_dkim_cname_records

        target_domain = settings.CONNECTION_INFO['SMTP']['HOST'].rstrip('.')
        target_domain_fqdn = f'{target_domain}.'
        spf_host = (settings.SPF_HOST or '').rstrip('.')
        normalized_cust_domain = cust_domain.rstrip('.')
        mx_name = '@' if len(normalized_cust_domain.split('.')) == 2 else f'{normalized_cust_domain}.'

        records = [
            {'type': 'MX', 'name': mx_name, 'content': target_domain_fqdn, 'priority': '10'},
            {
                'type': 'SRV',
                'name': f'_jmap._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_caldavs._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_carddavs._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_imaps._tcp.{normalized_cust_domain}.',
                'content': f'1 993 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_submission._tcp.{normalized_cust_domain}.',
                'content': f'1 587 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'TXT',
                'name': f'{normalized_cust_domain}.',
                'content': f'v=spf1 include:{spf_host} -all',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_mta-sts.{normalized_cust_domain}.',
                'content': 'v=STSv1; id=18139500144460329770',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_smtp._tls.{normalized_cust_domain}.',
                'content': f'v=TLSRPTv1; rua=mailto:postmaster@{normalized_cust_domain}',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_dmarc.{normalized_cust_domain}.',
                'content': 'v=DMARC1; p=none;',
                'priority': '-',
            },
        ]

        records.extend(build_customer_dkim_cname_records(normalized_cust_domain))
        return records

    def check_domain_dns(self, domain_name: str) -> dict:
        """Check expected DNS records and return verification details for a custom domain.

        TODO: Remove this out of api client."""
        expected_records = self.build_expected_dns_records(domain_name)
        dns_records = enrich_dns_records_with_status(domain_name, expected_records)
        critical_errors = []
        warnings = []

        mx_records = [record for record in dns_records if record.get('type') == 'MX']
        if not any(record.get('status') == DNSRecordStatus.MATCH.value for record in mx_records):
            critical_errors.append(DomainVerificationErrors.MX_LOOKUP_ERROR)

        spf_records = [
            record
            for record in dns_records
            if record.get('type') == 'TXT' and record.get('content', '').startswith('v=spf1')
        ]
        if not any(record.get('status') == DNSRecordStatus.MATCH.value for record in spf_records):
            warnings.append(DomainVerificationErrors.SPF_RECORD_NOT_FOUND)

        dkim_records = [record for record in dns_records if '_domainkey' in record.get('name', '')]
        if not dkim_records or any(record.get('status') != DNSRecordStatus.MATCH.value for record in dkim_records):
            critical_errors.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)

        is_verified = len(critical_errors) == 0
        return {
            'is_verified': is_verified,
            'critical_errors': critical_errors,
            'warnings': warnings,
            'dns_records': dns_records,
        }

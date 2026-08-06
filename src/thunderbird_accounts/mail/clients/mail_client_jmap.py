from abc import ABC
import json
import logging
import uuid
from typing import Optional, Type

import sentry_sdk
from django.conf import settings
from pydantic import BaseModel, ValidationError

from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.clients.mail_client_interface import MailClientInterface
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
    AccountSetError,
    AppPasswordSetError,
    DomainAlreadyExistsError,
    DomainNotFoundError,
    DomainSetError,
    InvalidJMapResponseError,
    JMapError,
)
from thunderbird_accounts.mail.types import stalwart
from thunderbird_accounts.mail.types.jmap import Invocation, JMapRequest
from thunderbird_accounts.mail.types.stalwart import AppPassword, SecondaryCredential, StalwartMethods, StalwartType


class BaseJMAP(ABC):
    client: JMAPClient
    account_id: Optional[str] = None
    primary_domain_id: Optional[str] = None

    def _get_user_client(
        self, username, user_token, auth_type: JMAPClient.AUTH_TYPES = JMAPClient.AUTH_TYPES.BEARER
    ) -> JMAPClient:
        client = JMAPClient('http://localhost:8080', username, user_token, auth_type)
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
        with open(f'd_{name}.json', 'w') as fh:
            fh.write(json.dumps(data, indent=2))

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
    def __init__(self):
        self.client = self._get_user_client('admin', 'admin', JMAPClient.AUTH_TYPES.BASIC)
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

    def create_domain(self, domain, description='') -> stalwart.Id:
        self.preflight_check()

        # If the domain already exists, we ignore and return None
        try:
            self.get_domain(domain)
            raise DomainAlreadyExistsError(domain)
        except DomainNotFoundError:
            pass

        domain = stalwart.DomainCreate(
            name=domain,
            is_enabled=True,
            description=description,
            aliases={},
            certificate_management=stalwart.StalwartType(type='Manual'),
            dkim_management=stalwart.StalwartType(type='Automatic'),
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

    def delete_domain(self, domain_name: str) -> None:

        # Allow DomainNotFound to raise if the domain is not found
        domain = self.get_domain(domain_name)
        if not domain.id:
            raise DomainNotFoundError(domain_name)

        try:
            dkim_signatures = self.get_dkim_signatures(domain_name)
            dkim_signature_ids = [signature.id for signature in dkim_signatures]
            self._handle_destroy(StalwartMethods.DKIM_SIGNATURE, dkim_signature_ids)  # ty: ignore[invalid-argument-type]
        except RuntimeError:
            pass

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
    ) -> stalwart.Id:
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

        return response.method_responses[1].arguments.get('list', [])

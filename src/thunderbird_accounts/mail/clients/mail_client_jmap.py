from django.conf import settings
import uuid
from typing import Optional, Type
import sentry_sdk
from pydantic import ValidationError
import json
import logging
from thunderbird_accounts.mail.exceptions import (
    DomainNotFoundError,
    InvalidJMapResponseError,
    AccountNotFoundError,
    AccountSetError,
    JMapError,
)
from thunderbird_accounts.mail.types import stalwart
from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.types.jmap import JMapRequest, Invocation
from thunderbird_accounts.mail.clients.mail_client_interface import MailClientInterface


class MailClientJMAP(MailClientInterface):
    def __init__(self):
        self.client = JMAPClient('http://localhost:8080', 'admin', 'admin', JMAPClient.AUTH_TYPES.BASIC)
        self.account_id = None
        self.primary_domain_id = None

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
                        name='x:Domain/query',
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
            name='x:Account/query',
            arguments={
                'accountId': self.account_id,
                'filter': {'name': account_name, 'domainId': self.primary_domain_id},
                'limit': 5,
                'position': 0,
                'calculateTotal': True,
            },
            method_call_id=method_call_id,
        )

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
                        name='x:Domain/query',
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
                        name='x:Domain/get',
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
        self._debug_dump('get_domain', data)

        try:
            return stalwart.Domain(**data)
        except ValidationError as ex:
            logging.warning(f'[MailClient.get_domain({domain}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex)

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
                        name='x:Account/get',
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
        self._debug_dump('get_account', data)

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
    ):
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
        domain_names = [account_domain]
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
                        name='x:Domain/query',
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

        aliases = {
            str(idx): stalwart.EmailAlias(
                enabled=True, name=email.split('@')[0], domain_id=domain_ids_by_domain[email.split('@')[1]]
            )
            for idx, email in enumerate(emails)
        }
        data = stalwart.Account(
            type=stalwart.Account.Types.USER.value,
            id=None,
            name=account_name,
            description=full_name,
            encryption_at_rest=stalwart.StalwartType(type='Disabled'),
            roles=stalwart.StalwartType(type='User'),
            permissions=stalwart.StalwartType(type='Inherit'),
            domain_id=domain_ids_by_domain[account_domain],
            aliases=aliases,
            quotas={'maxDiskQuota': quota} if quota else None,
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
                        name='x:Account/set',
                        arguments={
                            'accountId': self.account_id,
                            'create': {
                                temp_id: {
                                    **data.model_dump(exclude_none=True),
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
        self._debug_dump('set_account', data)

        stalwart_pkid = data.get(temp_id, {}).get('id')

        # Just in case the account was not created and Stalwart missed an error check
        if not stalwart_pkid:
            raise AccountNotFoundError(principal_id)

        return stalwart_pkid

    def _patch_account(self, principal_id: str, data: stalwart.Account):
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
                        name='x:Account/set',
                        arguments={
                            'accountId': self.account_id,
                            'update': {
                                stalwart_pkid: {
                                    **data.model_dump(exclude_none=True),
                                }
                            },
                        },
                        method_call_id='0',
                    ),
                ],
            )
        )

        print('->', response)
        data = response.method_responses[0].arguments.get('updated', {})
        self._debug_dump('patch_account', data)

        return data

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> None:
        """Updates Stalwart and changes their primary email address and/or full name"""

        account = stalwart.AccountUpdate(
            name=primary_email_address or None,
            description=full_name or None
        )

        if not account.name and not account.description:
            raise ValueError('You must provide at least one field to change.')

        self._patch_account(principal_id, account)

        # Returns data: null on success...
        #data = response.json()
        #error = data.get('error')
        # I have no idea what the error is yet
        #if error:
        #    logging.error(f'[update_individual] err: {data}')
        #    raise RuntimeError(data)

    def delete_account(self, principal_id: str) -> None:
        """Deletes a Stalwart account from the given thundermail address.

        :raises AccountNotFoundError: If the account you're trying to delete does not exist.
        :raises AccountSetError: If there was a problem during the deletion process."""
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
                        name='x:Account/set',
                        arguments={
                            'accountId': self.account_id,
                            '#destroy': {'resultOf': '0', 'name': 'x:Account/query', 'path': '/ids'},
                        },
                        method_call_id='1',
                    ),
                ],
            )
        )

        # Account already deleted or doesn't exist? Raise a not found error
        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise AccountNotFoundError(principal_id)

        # Error during deletion
        error = response.method_responses[1].arguments.get('notDestroyed')
        if error:
            error_obj = list(error.values())[0]
            raise self._handle_jmap_error(error_obj, AccountSetError)

        print('->resp', response.method_responses)
        data = response.method_responses[1].arguments.get('destroyed', {})
        self._debug_dump('delete_account', data)

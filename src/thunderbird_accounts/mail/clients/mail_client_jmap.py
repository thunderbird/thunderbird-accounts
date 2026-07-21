from typing import Optional
import sentry_sdk
from pydantic import ValidationError
import json
import logging
from thunderbird_accounts.mail.exceptions import DomainNotFoundError, InvalidJMapResponseError, AccountNotFoundError
from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.clients.stalwart_types import DomainType, AccountType, EmailAlias, StalwartType
from thunderbird_accounts.mail.clients.jmap_types import JMapRequest, Invocation, ResponseIndex
from thunderbird_accounts.mail.clients.mail_client_interface import MailClientInterface


class MailClientJMAP(MailClientInterface):
    def __init__(self):
        self.client = JMAPClient('http://localhost:8080', 'admin', 'admin', JMAPClient.AUTH_TYPES.BASIC)
        self.account_id = None
        pass

    def _get_session(self):
        session = self.client.get_session()

        # Retrieve our account from the primary account for jmap calls
        self.account_id = session.get('primaryAccounts', {}).get('urn:stalwart:jmap')
        if not self.account_id:
            self.account_id = list(session.get('accounts', {}).keys())[0]

    def preflight_check(self):
        if not self.account_id:
            self._get_session()

    def _debug_dump(self, name: str, data: dict):
        with open(f'd_{name}.json', 'w') as fh:
            fh.write(json.dumps(data, indent=2))

    def get_domain(self, domain) -> DomainType:
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
            return DomainType(**data)
        except ValidationError as ex:
            logging.warning(f'[MailClient.get_domain({domain}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex)

    def get_account(self, principal_id: str) -> AccountType:
        self.preflight_check()

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                ],
                method_calls=[
                    Invocation(
                        name='x:Account/query',
                        arguments={
                            'accountId': self.account_id,
                            'filter': {'name': principal_id},
                            'limit': 25,
                            'position': 0,
                            'calculateTotal': True,
                        },
                        method_call_id='0',
                    ),
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
            return AccountType(**data)
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
        self.preflight_check()

        account_name, domain_name = principal_id.split('@')

        domain_lookup_rq = Invocation(
            name='x:Domain/query',
            arguments={
                'accountId': self.account_id,
                'filter': {'name': domain_name},
                'limit': 25,
                'position': 0,
                'calculateTotal': True,
            },
            method_call_id='0',
        )

        aliases = {str(idx): EmailAlias(enabled=True, name=email, domainId='a') for idx, email in enumerate(emails)}
        data = AccountType(
            type=AccountType.Types.USER.value,
            id=None,
            name=account_name,
            description=full_name,
            encryptionAtRest=StalwartType(type='Disabled'),
            roles=StalwartType(type='User'),
            permissions=StalwartType(type='Inherit'),
            locale='en_US',
            domainId='b',
        )

        invocations = [
            #domain_lookup_rq,
            Invocation(
                name='x:Account/set',
                arguments={
                    'accountId': self.account_id,
                    'create': {
                        'new-1': {
                            **data.model_dump(exclude_none=True),
                            #'#domainId': {'resultOf': '0', 'name': 'x:Domain/query', 'path': '/ids/0'},
                        }
                    },
                },
                method_call_id='1',
            ),
        ]

        response = self.client.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:stalwart:jmap',
                    'urn:ietf:params:jmap:blob',
                    'urn:ietf:params:jmap:mail',
                    'urn:ietf:params:jmap:calendars',
                    'urn:ietf:params:jmap:contacts',
                    'urn:ietf:params:jmap:principals',
                    'urn:ietf:params:jmap:sieve',
                    'urn:ietf:params:jmap:vacationresponse',
                ],
                method_calls=invocations,
            )
        )
        print('RESPONSE->', response)
        data = response.method_responses[1].arguments.get('list', [])[0]
        self._debug_dump('set_account', data)
        if not response.method_responses or response.method_responses[0].arguments.get('total') == 0:
            raise AccountNotFoundError(principal_id)

        try:
            return AccountType(**data)
        except ValidationError as ex:
            logging.warning(f'[MailClient.get_account({principal_id}]: Failed pydantic validation!')
            sentry_sdk.capture_exception(ex)
            raise InvalidJMapResponseError(ex)

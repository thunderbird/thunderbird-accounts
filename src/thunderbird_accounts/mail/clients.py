import base64
import json
import logging
from enum import StrEnum
from typing import Optional

import requests
from django.conf import settings
from django.utils.crypto import get_random_string

from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError, StalwartError


class StalwartErrors(StrEnum):
    """Errors defined in Stalwart's management api
    https://github.com/stalwartlabs/stalwart/blob/4d819a1041b0adfce3757df50929764afa10e27b/crates/http/src/management/mod.rs#L58
    """

    FIELD_ALREADY_EXISTS = 'fieldAlreadyExists'
    FIELD_MISSING = 'fieldMissing'
    NOT_FOUND = 'notFound'
    UNSUPPORTED = 'unsupported'
    ASSERT_FAILED = 'assertFailed'
    OTHER = 'other'


class MailClient:
    """A partial api client for Stalwart
    Docs: https://stalw.art/docs/api/management/endpoints
    Code: https://github.com/stalwartlabs/stalwart/tree/main/crates/http/src/management

    Important note: The principal_id field is principal object's name, not auto-incremented id!
    """

    def __init__(self):
        self.api_url = f'{settings.STALWART_BASE_API_URL}/api'
        self.api_auth_string = settings.STALWART_API_AUTH_STRING
        self.api_auth_method = settings.STALWART_API_AUTH_METHOD

        # Sanity check
        assert self.api_auth_method in ['basic', 'bearer']

        self.authorized_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'{self.api_auth_method} {self.api_auth_string}',
        }

    def _raise_for_error(self, response):
        data = response.json()
        error = data.get('error')
        # Only catch 'other' errors here
        if error == StalwartErrors.OTHER.value:
            details_and_reason = ': '.join([data.get('details'), data.get('reason')])
            raise StalwartError(details_and_reason)

    def _list_principals(self, page=1, limit=100, type: Optional[str] = None) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints/#list-principals

        Important: Don't use this directly!
        """
        params = {'page': page, 'limit': limit}
        if type:
            params['type'] = type

        response = requests.get(
            f'{self.api_url}/principal', params=params, headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        # Reduce log spam
        # logging.info(f'[MailClient._list_principals()]: {response.json()}')

        return response

    def _get_principal(self, principal_id: str) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#fetch-principal

        Important: Don't use this directly!
        """
        response = requests.get(
            f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        return response

    def _delete_principal(self, principal_id: str) -> requests.Response:
        """Deletes a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints/#delete-principal

        Important: Don't use this directly!
        """
        response = requests.delete(
            f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        return response

    def _create_principal(self, principal_data: dict):
        """Returns a response for the creation of a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#create-principal

        Important: Don't use this directly!
        """
        if not any([principal_data.get('type', principal_data.get('name'))]):
            raise TypeError('Principal object must contain type AND name.')

        principal_data = {
            'quota': 0,
            'secrets': [],
            'emails': [],
            'urls': [],
            'memberOf': [],
            'roles': [],
            'lists': [],
            'members': [],
            'enabledPermissions': [],
            'disabledPermissions': [],
            'externalMembers': [],
            **principal_data,
        }

        response = requests.post(
            f'{self.api_url}/principal/deploy', json=principal_data, headers=self.authorized_headers, verify=False
        )

        response.raise_for_status()
        self._raise_for_error(response)

        return response

    def _update_principal(self, principal_id: str, update_data: list[dict]):
        patch_schema = {
            'type': ('set',),
            'name': ('set',),
            'description': ('set',),
            'quota': ('set',),
            'secrets': ('addItem', 'removeItem'),
            'emails': ('addItem', 'removeItem'),
            'urls': ('addItem', 'removeItem'),
            'memberOf': ('addItem', 'removeItem'),
            'roles': ('addItem', 'removeItem'),
            'lists': ('addItem', 'removeItem'),
            'members': ('addItem', 'removeItem'),
            'enabledPermissions': ('addItem', 'removeItem'),
            'disabledPermissions': ('addItem', 'removeItem'),
            'externalMembers': ('addItem', 'removeItem'),
        }

        # TODO: Look into bringing in pydantic to handle schema validation
        for data in update_data:
            allowed_actions = patch_schema.get(data.get('field'))
            if data.get('action') not in allowed_actions:
                raise TypeError(f'{data.get("action")} is not allowed in')

        response = requests.patch(
            f'{self.api_url}/principal/{principal_id}', json=update_data, headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        return response

    def get_telemetry(self):
        """We actually only use this for the health check"""
        response = requests.patch(
            f'{self.api_url}/telemetry/metrics', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)
        return response

    def _parse_verification_stages(self, stages: list) -> tuple[bool, list[str]]:
        """Parse Stalwart verification stages to determine success/failure.

        Ref https://github.com/stalwartlabs/webadmin/blob/main/src/pages/manage/troubleshoot.rs#L806-L1003

        Based on Stalwart's DeliveryStage enum, stages are categorized as:
        - Success stages (e.g., MxLookupSuccess, ConnectionSuccess)
        - Error stages (e.g., MxLookupError, ConnectionError) - actual failures
        - NotFound stages (e.g., MtaStsNotFound, TlsaNotFound) - warnings, not failures

        For domain verification, we only fail on CRITICAL errors that prevent basic SMTP:
        - MX/IP lookup failures
        - Connection failures
        - SMTP protocol failures (EHLO, etc.)

        Advanced security features (MTA-STS, TLSA, TLS-RPT) are optional and won't fail verification.

        Args:
            stages: List of stage dictionaries from Stalwart troubleshooting API

        Returns:
            tuple: (is_verified, failed_stages)
                - is_verified: True if verification completed successfully
                - failed_stages: List of stage types that had errors/warnings
        """
        if not stages:
            return False, []

        critical_errors = set()
        warnings = set()
        has_completed = False

        # Critical errors that prevent basic SMTP delivery (will fail verification)
        critical_error_types = {
            'mxLookupError',        # Can't find mail servers
            'ipLookupError',        # Can't resolve IP addresses
            'connectionError',      # Can't connect to server
            'readGreetingError',    # SMTP greeting failed
            'ehloError',            # EHLO command failed
        }

        # Optional/advanced features that are warnings but don't fail verification
        # These include NotFound variants and errors for optional security features
        warning_types = {
            # NotFound variants (expected to be missing for many domains)
            'mtaStsNotFound',       # MTA-STS policy not published (optional)
            'tlsRptNotFound',       # TLS-RPT record not published (optional)
            'tlsaNotFound',         # TLSA/DANE records not found (optional)
            # Optional security feature errors
            'mtaStsFetchError',     # Failed to fetch MTA-STS policy (optional)
            'mtaStsVerifyError',    # MTA-STS verification failed (optional)
            'tlsRptLookupError',    # TLS-RPT lookup failed (optional)
            'tlsaLookupError',      # TLSA lookup failed (optional)
            'daneVerifyError',      # DANE verification failed (optional)
            # StartTLS is important but many servers work without it
            'startTlsError',        # TLS upgrade failed (degraded security but may work)
        }

        for stage in stages:
            if not isinstance(stage, dict):
                continue

            stage_type = stage.get('type', '')

            # Check if process completed successfully
            if stage_type == 'completed':
                has_completed = True
                continue

            # Categorize the stage
            if stage_type in critical_error_types:
                critical_errors.add(stage_type)
            elif stage_type in warning_types:
                warnings.add(stage_type)
            # Catch any other error types not explicitly categorized
            elif stage_type.endswith('Error') and stage_type not in warning_types:
                # MailFromError, RcptToError would be critical if we tested full delivery
                # But for domain verification, we typically stop at EHLO/StartTLS
                critical_errors.add(stage_type)

        # Verification succeeds if:
        # 1. The troubleshooting process completed (reached 'completed' stage)
        # 2. There are no CRITICAL errors (optional security features don't count)
        is_verified = has_completed and len(critical_errors) == 0

        return is_verified, list(critical_errors), list(warnings)

    def get_domain(self, domain):
        response = self._get_principal(domain)

        data = response.json()
        error = data.get('error')

        logging.info(f'[MailClient.get_domain({domain}]: {data}')

        if error == StalwartErrors.NOT_FOUND.value:
            raise DomainNotFoundError(domain)

        assert data.get('data', {}).get('type') == 'domain'

        return data

    def create_dkim(self, domain):
        data = {'id': None, 'algorithm': settings.STALWART_DKIM_ALGO, 'domain': domain, 'selector': None}
        response = requests.post(f'{self.api_url}/dkim', json=data, headers=self.authorized_headers, verify=False)
        response.raise_for_status()
        data = response.json()
        return data.get('data')

    def create_account(
        self,
        emails: list[str],
        principal_id: str,
        full_name: Optional[str] = None,
        app_password: Optional[str] = None,
        quota: Optional[int] = None,
    ):
        data = {
            'type': 'individual',
            'name': principal_id,
            'description': full_name,
            'emails': emails,
            'roles': ['user'],
        }
        if quota:
            data['quota'] = quota
        if app_password:
            data['secrets'] = [app_password]
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def get_account(self, principal_id: str) -> dict:
        response = self._get_principal(principal_id)

        data = response.json()
        error = data.get('error')

        if error == StalwartErrors.NOT_FOUND.value:
            raise AccountNotFoundError(principal_id)

        assert data.get('data', {}).get('type') == 'individual'

        # Return the pkid
        return data.get('data')

    def delete_account(self, principal_id: str):
        """Deletes a Stalwart principal object from the given principal_id"""
        return self._delete_principal(principal_id)

    def delete_app_password(self, principal_id: str, secret: str):
        response = self._update_principal(
            principal_id,
            [{'action': 'removeItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[delete_app_password] err: {data}')
            raise RuntimeError(data)

    def save_app_password(self, principal_id: str, secret: str):
        response = self._update_principal(
            principal_id,
            [{'action': 'addItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[save_app_password] err: {data}')
            raise RuntimeError(data)

    def save_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Adds a new email address to a stalwart's individual principal by uuid."""

        if isinstance(emails, str):
            emails = [emails]

        response = self._update_principal(
            principal_id,
            [{'action': 'addItem', 'field': 'emails', 'value': email} for email in emails],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[save_email_addresses] err: {data}')
            raise RuntimeError(data)

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]):
        """Replaces an email address with a new one from a stalwart's individual principal by uuid."""

        actions = []
        for old_email, email in emails:
            actions.append({'action': 'removeItem', 'field': 'emails', 'value': old_email})
            actions.append({'action': 'addItem', 'field': 'emails', 'value': email})

        response = self._update_principal(principal_id, actions)
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[replace_email_addresses] err: {data}')
            raise RuntimeError(data)

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Deletes an address from a stalwart's individual principal by uuid."""

        if isinstance(emails, str):
            emails = [emails]

        response = self._update_principal(
            principal_id,
            [{'action': 'removeItem', 'field': 'emails', 'value': email} for email in emails],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[delete_email_addresses] err: {data}')
            raise RuntimeError(data)

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        """Updates Stalwart and changes their primary email address and/or full name"""

        update_data = []
        if primary_email_address:
            update_data.append(
                {'action': 'set', 'field': 'name', 'value': primary_email_address},
            )
        if full_name:
            update_data.append(
                {'action': 'set', 'field': 'description', 'value': full_name},
            )

        if len(update_data) == 0:
            raise ValueError('You must provide at least one field to change.')

        response = self._update_principal(principal_id, update_data)

        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[update_individual] err: {data}')
            raise RuntimeError(data)

    def update_quota(self, principal_id: str, quota: int):
        update_data = [
            {'action': 'set', 'field': 'quota', 'value': quota},
        ]
        response = self._update_principal(principal_id, update_data)

        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[update_individual] err: {data}')
            raise RuntimeError(data)

    def make_api_key(self, principal_id, password):
        if not settings.IS_DEV:
            raise RuntimeError('You can only make api keys in dev.')

        basic_auth = base64.b64encode(f'{principal_id}:{password}'.encode()).decode()
        self.authorized_headers['Authorization'] = f'Basic {basic_auth}'

        api_key_name = 'tb-accounts-api-key'
        secret = get_random_string(32)
        data = {'type': 'apiKey', 'name': api_key_name, 'secrets': [secret], 'roles': ['admin']}

        response = self._create_principal(data)
        data = response.json()
        if data.get('error'):
            raise StalwartError(data.get('error'))

        response = self._get_principal(api_key_name)
        data = response.json()

        if not data.get('data', {}).get('id'):
            raise RuntimeError("Error calling stalwart's api")

        return base64.b64encode(f'{api_key_name}:{secret}'.encode()).decode()

    def create_domain(self, domain, description=''):
        data = {
            'type': 'domain',
            'name': domain,
            'description': description,
        }
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def delete_domain(self, domain_name: str):
        """Deletes a Stalwart domain object from the given domain_name"""
        response = self._delete_principal(domain_name)
        data = response.json()
        error = data.get('error')

        if error:
            logging.error(f'[delete_domain] err: {data}')
            raise RuntimeError(data)

    def get_dns_records(self, domain_name: str) -> list[dict]:
        response = requests.get(
            f'{self.api_url}/dns/records/{domain_name}', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)
        data = response.json()
        return data.get('data')

    def verify_domain(self, domain_name: str):
        """Verify domain using Stalwart's troubleshooting API with SSE streaming.

        This implementation follows the Stalwart web-admin approach:
        1. Get a troubleshooting token
        2. Stream delivery stages via SSE
        3. Collect stages until completion

        Args:
            domain_name: The domain to verify/troubleshoot

        Returns:
            tuple: (is_verified, critical_errors, warnings)
                - is_verified: True if verification completed successfully
                - critical_errors: List of stage types that had errors
                - warnings: List of stage types that had warnings
        """
        # Step 1: Get troubleshooting token
        token_response = requests.get(
            f'{self.api_url}/troubleshoot/token',
            headers=self.authorized_headers,
            verify=False
        )
        token_response.raise_for_status()
        auth_token = token_response.json()

        # Step 2: Stream delivery stages via SSE
        sse_url = f'{self.api_url}/troubleshoot/delivery/{domain_name}?token={auth_token}'
        sse_response = requests.get(
            sse_url,
            headers={
                **self.authorized_headers,
                'Accept': 'text/event-stream',
            },
            stream=True,
            verify=False
        )
        sse_response.raise_for_status()

        # Step 3: Parse SSE events and collect delivery stages
        delivery_stages = []
        current_event = None
        event_data = []

        for line in sse_response.iter_lines(decode_unicode=True):
            if line is None:
                continue

            # Empty line signals end of event
            if not line.strip():
                if event_data and current_event == 'event':
                    # Parse the JSON data
                    data_content = '\n'.join(event_data)
                    try:
                        stages = json.loads(data_content)
                        if isinstance(stages, list):
                            for stage in stages:
                                delivery_stages.append(stage)
                                # Check for completion
                                if isinstance(stage, dict) and stage.get('type') == 'Completed':
                                    return delivery_stages
                                elif isinstance(stage, str) and stage == 'Completed':
                                    return delivery_stages
                    except json.JSONDecodeError as e:
                        logging.warning(f'Failed to parse SSE data: {e}')

                # Reset for next event
                event_data = []
                current_event = None
                continue

            # Parse SSE fields
            if line.startswith('event:'):
                current_event = line[6:].strip()
            elif line.startswith('data:'):
                event_data.append(line[5:].strip())

        print(delivery_stages)

        # Parse the verification stages to determine success/failure
        is_verified, critical_errors, warnings = self._parse_verification_stages(delivery_stages)
        return is_verified, critical_errors, warnings

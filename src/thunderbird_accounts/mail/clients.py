import base64
import dns.resolver
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


class DomainVerificationErrors(StrEnum):
    """Domain verification error codes returned by verify_domain()"""

    # Critical errors (fail verification)
    MX_LOOKUP_ERROR = 'mxLookupError'

    # Warnings (do not fail verification)
    SPF_RECORD_NOT_FOUND = 'spfRecordNotFound'
    DKIM_RECORD_NOT_FOUND = 'dkimRecordNotFound'


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
            f'{self.api_url}/principal',
            params=params,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
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
            f'{self.api_url}/principal/{principal_id}',
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
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
            f'{self.api_url}/principal/{principal_id}',
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
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
            f'{self.api_url}/principal/deploy',
            json=principal_data,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
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
            if allowed_actions and data.get('action') not in allowed_actions:
                raise TypeError(f'{data.get("action")} is not allowed in')

        response = requests.patch(
            f'{self.api_url}/principal/{principal_id}',
            json=update_data,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        self._raise_for_error(response)

        return response

    def get_telemetry(self):
        """We actually only use this for the health check"""
        response = requests.patch(
            f'{self.api_url}/telemetry/metrics',
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        self._raise_for_error(response)
        return response

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
        response = requests.post(
            f'{self.api_url}/dkim',
            json=data,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        data = response.json()
        return data.get('data')

    def delete_dkim(self, domain) -> Optional[requests.Response]:
        """
        Removes all dkim signatures for a given domain from Stalwart.

        Returns None if there's nothing to delete, otherwise returns the delete response.
        """

        # Look up dkim signatures related to this domain
        data = {'suffix': 'algorithm', 'prefix': 'signature', 'filter': domain, 'limit': 50, 'page': 1}
        response = requests.get(
            f'{self.api_url}/settings/group',
            params=data,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()

        response_data = response.json().get('data')
        if not response_data or not response_data.get('total'):
            return None

        # Dict comprehension to remove any duplicate _ids (there shouldn't be any, but I have trust issues.)
        dkim_ids = {r.get('_id'): True for r in response_data.get('items', [])}

        data = [{'type': 'clear', 'prefix': f'signature.{d}.'} for d in dkim_ids.keys()]
        response = requests.post(
            f'{self.api_url}/settings',
            json=data,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()

        return response

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

        if error == StalwartErrors.NOT_FOUND.value:
            raise DomainNotFoundError(domain_name)
        elif error:
            logging.error(f'[delete_domain] err: {data}')
            raise RuntimeError(data)

    def get_dns_records(self, domain_name: str) -> list[dict]:
        response = requests.get(
            f'{self.api_url}/dns/records/{domain_name}',
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        self._raise_for_error(response)
        data = response.json()
        return data.get('data')

    def verify_domain(self, domain_name: str):
        """Verify domain using dnspython.

        Checks:
        1. MX Records exist and point to the correct host (Critical, fails verification)
        2. SPF Record exists and includes the correct host (Warning if missing)
        3. DKIM Record exists (Warning if missing)

        Returns:
            tuple: (is_verified, critical_errors, warnings)
                - is_verified: True if verification completed successfully without critical errors
                - critical_errors: List of errors (e.g., DomainVerificationErrors.MX_LOOKUP_ERROR)
                - warnings: List of warnings (e.g., DomainVerificationErrors.SPF_RECORD_NOT_FOUND)
        """
        critical_errors = []
        warnings = []

        expected_host = settings.CONNECTION_INFO['SMTP']['HOST'].rstrip('.')

        # 1. Check MX Records
        try:
            mx_answers = dns.resolver.resolve(domain_name, 'MX')
            has_correct_mx = False
            for rdata in mx_answers:
                exchange = rdata.exchange.to_text().rstrip('.')
                if exchange == expected_host:
                    has_correct_mx = True
                    break

            if not has_correct_mx:
                logging.warning(f'MX records found for {domain_name} but none match {expected_host}')
                critical_errors.append(DomainVerificationErrors.MX_LOOKUP_ERROR)

        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            critical_errors.append(DomainVerificationErrors.MX_LOOKUP_ERROR)
        except Exception as e:
            logging.error(f'MX lookup failed for {domain_name}: {e}')
            critical_errors.append(DomainVerificationErrors.MX_LOOKUP_ERROR)

        # 2. Check SPF Record
        try:
            txt_answers = dns.resolver.resolve(domain_name, 'TXT')
            has_spf = False
            expected_spf_include = f'include:spf.{expected_host}'

            for rdata in txt_answers:
                # rdata.strings is a list of bytes
                txt_content = b''.join(rdata.strings).decode('utf-8')
                if txt_content.startswith('v=spf1') and expected_spf_include in txt_content:
                    has_spf = True
                    break

            if not has_spf:
                warnings.append(DomainVerificationErrors.SPF_RECORD_NOT_FOUND)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            warnings.append(DomainVerificationErrors.SPF_RECORD_NOT_FOUND)
        except Exception as e:
            logging.warning(f'SPF lookup failed for {domain_name}: {e}')
            warnings.append(DomainVerificationErrors.SPF_RECORD_NOT_FOUND)

        # 3. Check DKIM Record
        # We need to get the selector first from Stalwart
        # Since we don't store the selector in our DB, we'll fetch DNS records
        # from Stalwart which generates the expected records
        try:
            stalwart_dns_records = self.get_dns_records(domain_name)

            dkim_record = next(
                (r for r in stalwart_dns_records if r.get('type') == 'TXT' and '_domainkey' in r.get('name', '')), None
            )

            if dkim_record:
                # name comes back like "selector._domainkey.domain.com."
                # we need to query "selector._domainkey.domain.com"
                dkim_host = dkim_record['name'].rstrip('.')

                txt_answers = dns.resolver.resolve(dkim_host, 'TXT')
                has_dkim = False
                expected_p_value = None

                # Extract p= value from expected dkim record
                parts = [p.strip() for p in dkim_record.get('content', '').split(';')]
                for part in parts:
                    if part.startswith('p='):
                        expected_p_value = part[2:]
                        break

                if not expected_p_value:
                    logging.warning(f'Could not extract p value from expected DKIM record for {domain_name}')
                    warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)
                else:
                    # The value from stalwart might be split or formatted differently, so we mainly check
                    # if a TXT record exists and if it looks like a DKIM record (v=DKIM1) and has matching p
                    for rdata in txt_answers:
                        txt_content = b''.join(rdata.strings).decode('utf-8')

                        if 'v=DKIM1' not in txt_content:
                            continue

                        # Extract p= value from DNS record
                        actual_p_value = None
                        parts = [p.strip() for p in txt_content.split(';')]

                        for part in parts:
                            if part.startswith('p='):
                                actual_p_value = part[2:]
                                break

                        if actual_p_value == expected_p_value:
                            has_dkim = True
                            break

                    if not has_dkim:
                        warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)
            else:
                # If we can't get the expected DKIM record from Stalwart, we can't verify it
                logging.warning(f'No DKIM record found in Stalwart for {domain_name}')
                warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)

        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)
        except Exception as e:
            logging.warning(f'DKIM lookup failed for {domain_name}: {e}')
            warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)

        is_verified = len(critical_errors) == 0
        return is_verified, critical_errors, warnings

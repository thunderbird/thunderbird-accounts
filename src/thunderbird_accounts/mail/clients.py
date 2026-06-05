import base64
import logging
from enum import StrEnum
from typing import Optional

import requests
from django.conf import settings
from django.utils.crypto import get_random_string

from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
    DomainNotFoundError,
    FailedToCreateDKIM,
    StalwartError,
)


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
    """Domain verification error codes returned by check_domain_dns()."""

    # Critical errors (fail verification)
    MX_LOOKUP_ERROR = 'mxLookupError'
    AUTODISCOVER_RECORD_FOUND = 'autodiscoverRecordFound'
    AUTODISCOVER_SRV_RECORD_FOUND = 'autodiscoverSrvRecordFound'

    # Warnings (do not fail verification)
    SPF_RECORD_NOT_FOUND = 'spfRecordNotFound'
    DKIM_RECORD_NOT_FOUND = 'dkimRecordNotFound'


class DkimSignatureStage(StrEnum):
    """Stalwart DKIM signature rotation stages."""

    PENDING = 'pending'
    ACTIVE = 'active'
    RETIRING = 'retiring'
    RETIRED = 'retired'


class DNSRecordStatus(StrEnum):
    MATCH = 'match'
    CONFLICT = 'conflict'
    MISSING = 'missing'
    UNKNOWN = 'unknown'


class StaleDNSRecordCode(StrEnum):
    """Stale DNS records that should be removed to prevent issues with the Thundermail setup."""

    AUTODISCOVER_CNAME_UNEXPECTED = 'autodiscoverCnameUnexpected'
    AUTODISCOVER_SRV_UNEXPECTED = 'autodiscoverSrvUnexpected'


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

        return data.get('data')

    def create_dkim(self, domain, stage: DkimSignatureStage = DkimSignatureStage.PENDING, algorithms=None):
        """
        Creates DKIM keys in Stalwart. Return list of response objects.
        Response objects may used for testing.
        Throws exception if request fails.
        """
        response_data = []
        dkim_algorithms = settings.STALWART_DKIM_ALGOS if algorithms is None else algorithms
        for algorithm in dkim_algorithms:
            data = {
                'id': None,
                'algorithm': algorithm,
                'domain': domain,
                'selector': settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm),
            }
            if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
                data['stage'] = stage.value

            response = requests.post(
                f'{self.api_url}/dkim',
                json=data,
                headers=self.authorized_headers,
                verify=settings.VERIFY_PRIVATE_LINK_SSL,
            )
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise FailedToCreateDKIM(algorithm, domain, str(exc)) from exc
            response_data.append(response.json().get('data'))
        return response_data

    def get_dkim_selectors(self, domain_name: str) -> set[str]:
        """Return DKIM selectors already present in Stalwart's DNS records."""
        selectors = set()
        domain_name = domain_name.rstrip('.').lower()
        suffix = f'._domainkey.{domain_name}'

        for record in self.get_dkim_dns_records(domain_name):
            if record.get('type') != 'TXT':
                continue

            record_name = record.get('name', '').rstrip('.').lower()
            if not record_name.endswith(suffix):
                continue

            selector = record_name[: -len(suffix)]
            if selector:
                selectors.add(selector)

        return selectors

    def ensure_dkim(self, domain_name: str, stage: DkimSignatureStage = DkimSignatureStage.PENDING) -> list[dict]:
        """Create only the configured DKIM selectors that are missing."""
        existing_selectors = self.get_dkim_selectors(domain_name)
        missing_algorithms = [
            algorithm
            for algorithm in settings.STALWART_DKIM_ALGOS
            if (settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm) or '').lower() not in existing_selectors
        ]

        if not missing_algorithms:
            return []

        return self.create_dkim(domain_name, stage=stage, algorithms=missing_algorithms)

    def activate_pending_dkim_signatures(self, domain_name: str) -> list[str]:
        """Activate pending DKIM signatures after their DNS records have been verified."""
        if not settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
            return []

        updates = {}
        for signature in self.get_dkim_signatures(domain_name):
            if signature.get('stage') != DkimSignatureStage.PENDING.value:
                continue

            signature_id = signature.get('id')
            if not signature_id:
                raise RuntimeError(f'Pending DKIM signature for {domain_name} did not include an id')

            updates[signature_id] = {'stage': DkimSignatureStage.ACTIVE.value}

        if not updates:
            return []

        response = self.make_jmap_admin_call(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:stalwart:jmap'],
                'methodCalls': [
                    [
                        'x:DkimSignature/set',
                        {'update': updates},
                        'u',
                    ],
                ],
            }
        )

        for method_name, arguments, _call_id in response.get('methodResponses', []):
            if method_name == 'x:DkimSignature/set':
                if arguments.get('notUpdated'):
                    raise RuntimeError(f'Stalwart failed to activate DKIM signatures: {arguments["notUpdated"]}')

                updated = arguments.get('updated') or {}
                return list(updated.keys()) if isinstance(updated, dict) else updated

            if method_name == 'error':
                raise RuntimeError(f'Stalwart JMAP error activating DKIM signatures: {arguments}')

        raise RuntimeError('Stalwart JMAP response did not include x:DkimSignature/set')

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

    def make_jmap_admin_call(self, call: dict) -> dict:
        response = requests.post(
            f'{settings.STALWART_BASE_JMAP_URL}/api',
            json=call,
            headers=self.authorized_headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        return response.json()

    def get_dkim_signatures(self, domain_name: str) -> list[dict]:
        domain = self.get_domain(domain_name)
        domain_id = domain.get('id')
        if not domain_id:
            raise RuntimeError(f'Stalwart domain {domain_name} did not include an id')

        response = self.make_jmap_admin_call(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:stalwart:jmap'],
                'methodCalls': [
                    [
                        'x:DkimSignature/query',
                        {'filter': {'domainId': domain_id}},
                        'q',
                    ],
                    [
                        'x:DkimSignature/get',
                        {'#ids': {'resultOf': 'q', 'name': 'x:DkimSignature/query', 'path': '/ids'}},
                        'g',
                    ],
                ],
            }
        )

        for method_name, arguments, _call_id in response.get('methodResponses', []):
            if method_name == 'x:DkimSignature/get':
                return arguments.get('list', [])
            if method_name == 'error':
                raise RuntimeError(f'Stalwart JMAP error fetching DKIM signatures: {arguments}')

        raise RuntimeError('Stalwart JMAP response did not include x:DkimSignature/get')

    def get_dkim_dns_records(self, domain_name: str) -> list[dict]:
        if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
            try:
                from thunderbird_accounts.mail.dkim import dkim_signatures_to_dns_records

                return dkim_signatures_to_dns_records(domain_name, self.get_dkim_signatures(domain_name))
            except DomainNotFoundError:
                logging.info(f'[MailClient.get_dkim_dns_records] {domain_name} is not a Stalwart domain yet')
            except Exception as ex:
                logging.warning(f'[MailClient.get_dkim_dns_records] Falling back to DNS records endpoint: {ex}')

        return [
            record
            for record in self.get_dns_records(domain_name)
            if record.get('type') == 'TXT' and '_domainkey' in record.get('name', '')
        ]

    def build_expected_dns_records(self, cust_domain: str) -> list[dict]:
        """Build the full list of DNS records the user must configure for a customer domain."""
        from thunderbird_accounts.mail.dkim import build_customer_dkim_cname_records

        target_domain = settings.CONNECTION_INFO['SMTP']['HOST'].rstrip('.')
        target_domain_fqdn = f'{target_domain}.'
        target_top_domain = '.'.join(target_domain.split('.')[1:])
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
                'content': f'v=spf1 include:spf.{target_top_domain} -all',
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
        """Check expected DNS records and return verification details for a custom domain."""
        # Circular import, so we import here
        from thunderbird_accounts.mail.dns import enrich_dns_records_with_status

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
            warnings.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)

        is_verified = len(critical_errors) == 0
        return {
            'is_verified': is_verified,
            'critical_errors': critical_errors,
            'warnings': warnings,
            'dns_records': dns_records,
        }

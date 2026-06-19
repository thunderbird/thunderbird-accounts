"""
Idempotently ensure the Keycloak realm is configured for MFA step-up.

The keycloak-mfa-rest step-up gate requires the realm to emit ``acr=2`` after an
authenticator (OTP) challenge. That depends on a browser authentication flow built
with Keycloak's *Conditional - Level of Authentication* executions, plus an
``acr.loa.map`` on the realm. A fresh realm gets this from the realm import JSON,
but existing realms (stage/prod, created before MFA) do not — and Keycloak's
``--import-realm`` skips realms that already exist. This command applies that
configuration to the running realm over the Admin API so deploys need no manual
Keycloak steps.

It is idempotent and safe to run on every deploy: it creates the step-up flow only
when missing, ensures ``acr.loa.map``, and binds the realm's browser flow. It is
fail-soft by default (logs and exits 0 if Keycloak is unreachable) so it never
blocks app startup; pass ``--strict`` to exit non-zero on failure.
"""

import logging
import time
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from thunderbird_accounts.authentication.clients import KeycloakClient

# Top-level flow we create and bind. Kept separate from the built-in "browser" flow
# so the original stays intact as a fallback (rebind the realm to "browser" to revert).
STEP_UP_FLOW_ALIAS = 'browser-mfa-stepup'

# Built in document order; mirrors the realm import's MFA step-up flow.
# (alias-or-provider, nesting level, requirement)
_DESIRED_REQUIREMENTS = [
    ('auth-cookie', 0, 'ALTERNATIVE'),
    ('identity-provider-redirector', 0, 'ALTERNATIVE'),
    ('stepup-forms', 0, 'ALTERNATIVE'),
    ('stepup-l1', 1, 'CONDITIONAL'),
    ('conditional-level-of-authentication', 2, 'REQUIRED'),
    ('auth-username-password-form', 2, 'REQUIRED'),
    ('stepup-l1-otp', 2, 'CONDITIONAL'),
    ('conditional-user-configured', 3, 'REQUIRED'),
    ('auth-otp-form', 3, 'REQUIRED'),
    ('stepup-l2', 1, 'CONDITIONAL'),
    ('conditional-level-of-authentication', 2, 'REQUIRED'),
    ('auth-otp-form', 2, 'ALTERNATIVE'),
    ('auth-recovery-authn-code-form', 2, 'ALTERNATIVE'),
]

# Level 2 (the OTP step-up) keeps loa-max-age=0 so Keycloak re-challenges the second
# factor on every step-up, refreshing the token's auth_time for the keycloak-mfa-rest
# freshness gate. Level 1's max-age is derived per-realm (see _loa_configs): it must
# match the SSO session lifespan, not a fixed value.
_LEVEL_2_LOA_CONFIG = ('mfa step-up level 2', {'loa-condition-level': '2', 'loa-max-age': '0'})

# Fallback L1 window when the realm doesn't report an SSO max lifespan (mirrors the import).
_DEFAULT_L1_MAX_AGE = 36000


class Command(BaseCommand):
    help = 'Idempotently configure the Keycloak realm browser flow + acr.loa.map for MFA step-up.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit non-zero if Keycloak is unreachable or configuration fails.',
        )

    def handle(self, *args, **options):
        strict = options['strict']
        if not settings.KEYCLOAK_API_ENDPOINT:
            logging.info('ensure_keycloak_mfa_flow: KEYCLOAK_API_ENDPOINT unset; skipping.')
            return

        self.realm_url = settings.KEYCLOAK_API_ENDPOINT.rstrip('/')
        try:
            self.token = self._token_with_retry()
            if self._already_configured():
                logging.info(
                    'ensure_keycloak_mfa_flow: realm browser flow already performs MFA step-up; nothing to do.'
                )
                return
            self._ensure_flow()
            self._ensure_acr_loa_map()
            self._ensure_browser_flow_bound()
            logging.info('ensure_keycloak_mfa_flow: realm MFA step-up configuration is in place.')
        except Exception as exc:
            logging.error(f'ensure_keycloak_mfa_flow: failed to configure realm: {exc}')
            if strict:
                raise

    # --- helpers ---------------------------------------------------------------

    def _token_with_retry(self, attempts: int = 6, delay_seconds: int = 5) -> str:
        """Keycloak may still be starting during a deploy; retry briefly before giving up."""
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                return KeycloakClient()._get_access_token()
            except requests.RequestException as exc:
                last_exc = exc
                logging.info(f'ensure_keycloak_mfa_flow: waiting for Keycloak ({attempt}/{attempts})')
                time.sleep(delay_seconds)
        raise last_exc

    def _req(self, method: str, path: str, json_data=None):
        url = f'{self.realm_url}/{path}' if path else self.realm_url
        response = requests.request(
            method=method,
            url=url,
            json=json_data,
            headers={'Accept': 'application/json', 'Authorization': f'Bearer {self.token}'},
        )
        response.raise_for_status()
        if response.content and response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        return None

    def _already_configured(self) -> bool:
        """True if the realm's bound browser flow already performs LoA step-up.

        Realms bootstrapped from the realm import already carry a step-up flow (with
        its own authenticator layout, e.g. recovery codes offered at the first OTP
        step), so we must not override it. Only realms missing it — existing
        stage/prod realms created before MFA — get the flow built and bound.
        """
        realm = self._req('GET', '')
        bound_alias = realm.get('browserFlow')
        if not bound_alias:
            return False
        executions = self._req('GET', f'authentication/flows/{quote(bound_alias)}/executions')
        return any(
            execution.get('providerId') == 'conditional-level-of-authentication' for execution in executions
        )

    def _ensure_flow(self):
        flows = self._req('GET', 'authentication/flows')
        if any(flow['alias'] == STEP_UP_FLOW_ALIAS for flow in flows):
            logging.info(f'ensure_keycloak_mfa_flow: flow "{STEP_UP_FLOW_ALIAS}" already present.')
            return

        logging.info(f'ensure_keycloak_mfa_flow: building flow "{STEP_UP_FLOW_ALIAS}".')
        self._req(
            'POST',
            'authentication/flows',
            {
                'alias': STEP_UP_FLOW_ALIAS,
                'providerId': 'basic-flow',
                'topLevel': True,
                'builtIn': False,
                'description': 'Browser flow with MFA step-up (LoA) for keycloak-mfa-rest',
            },
        )
        self._add_exec(STEP_UP_FLOW_ALIAS, 'auth-cookie')
        self._add_exec(STEP_UP_FLOW_ALIAS, 'identity-provider-redirector')
        self._add_subflow(STEP_UP_FLOW_ALIAS, 'stepup-forms', 'username/password + LoA step-up')
        self._add_subflow('stepup-forms', 'stepup-l1', 'first factor (LoA1)')
        self._add_subflow('stepup-forms', 'stepup-l2', 'OTP step-up (LoA2)')
        self._add_exec('stepup-l1', 'conditional-level-of-authentication')
        self._add_exec('stepup-l1', 'auth-username-password-form')
        self._add_subflow('stepup-l1', 'stepup-l1-otp', 'conditional OTP at L1')
        self._add_exec('stepup-l1-otp', 'conditional-user-configured')
        self._add_exec('stepup-l1-otp', 'auth-otp-form')
        self._add_exec('stepup-l2', 'conditional-level-of-authentication')
        self._add_exec('stepup-l2', 'auth-otp-form')
        self._add_exec('stepup-l2', 'auth-recovery-authn-code-form')

        self._apply_requirements_and_configs()

    def _add_exec(self, flow_alias: str, provider: str):
        self._req(
            'POST',
            f'authentication/flows/{quote(flow_alias)}/executions/execution',
            {'provider': provider},
        )

    def _add_subflow(self, parent_alias: str, alias: str, description: str):
        self._req(
            'POST',
            f'authentication/flows/{quote(parent_alias)}/executions/flow',
            {'alias': alias, 'type': 'basic-flow', 'description': description, 'provider': 'registration-page-form'},
        )

    def _apply_requirements_and_configs(self):
        executions = self._req('GET', f'authentication/flows/{quote(STEP_UP_FLOW_ALIAS)}/executions')
        used: set[int] = set()
        loa_execution_ids: list[str] = []

        for name, level, requirement in _DESIRED_REQUIREMENTS:
            for index, execution in enumerate(executions):
                if index in used or execution.get('level') != level:
                    continue
                is_match = execution.get('providerId') == name or (
                    execution.get('providerId') is None and execution.get('displayName') == name
                )
                if not is_match:
                    continue
                self._req(
                    'PUT',
                    f'authentication/flows/{quote(STEP_UP_FLOW_ALIAS)}/executions',
                    {'id': execution['id'], 'requirement': requirement},
                )
                used.add(index)
                if name == 'conditional-level-of-authentication':
                    loa_execution_ids.append(execution['id'])
                break
            else:
                raise RuntimeError(f'could not place execution {name} at level {level}')

        for execution_id, (alias, config) in zip(loa_execution_ids, self._loa_configs()):
            self._req('POST', f'authentication/executions/{execution_id}/config', {'alias': alias, 'config': config})

    def _loa_configs(self):
        """LoA condition configs, with the L1 window tied to this realm's session lifespan.

        The first factor must stay valid for the entire SSO session: if its window is
        shorter than ssoSessionMaxLifespan, a step-up to acr=2 on a still-valid session
        re-prompts username/password once the window lapses (the bug that bit the
        stage-seeded preview, whose 72h sessions outlived the import's fixed 10h window).
        Pinning L1 to ssoSessionMaxLifespan means it expires exactly when the session does.
        """
        realm = self._req('GET', '')
        session_max = realm.get('ssoSessionMaxLifespan') or _DEFAULT_L1_MAX_AGE
        return [
            ('mfa step-up level 1', {'loa-condition-level': '1', 'loa-max-age': str(session_max)}),
            _LEVEL_2_LOA_CONFIG,
        ]

    def _ensure_acr_loa_map(self):
        realm = self._req('GET', '')
        attributes = realm.get('attributes') or {}
        desired = '{"1":1,"2":2}'
        if attributes.get('acr.loa.map') == desired:
            return
        attributes['acr.loa.map'] = desired
        self._req('PUT', '', {**realm, 'attributes': attributes})
        logging.info('ensure_keycloak_mfa_flow: set realm acr.loa.map.')

    def _ensure_browser_flow_bound(self):
        realm = self._req('GET', '')
        if realm.get('browserFlow') == STEP_UP_FLOW_ALIAS:
            return
        self._req('PUT', '', {**realm, 'browserFlow': STEP_UP_FLOW_ALIAS})
        logging.info(f'ensure_keycloak_mfa_flow: bound realm browserFlow to "{STEP_UP_FLOW_ALIAS}".')

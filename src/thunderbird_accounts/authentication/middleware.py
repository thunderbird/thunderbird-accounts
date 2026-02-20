from requests.auth import HTTPBasicAuth
from json import JSONDecodeError
from urllib.parse import urlencode, quote
from django.utils.crypto import get_random_string
import requests
from time import time
from mozilla_django_oidc.middleware import SessionRefresh
from django.urls import reverse
from mozilla_django_oidc.utils import absolutify, import_from_settings, generate_code_challenge
import logging
from typing import Optional
from socket import gethostbyname, gethostname

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpRequest, JsonResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from .models import User
from .utils import is_email_in_allow_list

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.utils import add_state_and_verifier_and_nonce_to_session

OIDC_ACCESS_TOKEN_KEY = 'oidc_access_token'
OIDC_ID_TOKEN_KEY = 'oidc_id_token'
OIDC_REFRESH_TOKEN_KEY = 'oidc_refresh_token'


def store_tokens(request, access_token, id_token, refresh_token):
    """Store OIDC tokens.
    Mostly copy and paste from base package, but adjusted to live outside of OIDCAuthenticationBackend,
    and take in refresh_token
    """
    session = request.session

    if import_from_settings('OIDC_STORE_ACCESS_TOKEN', False):
        session[OIDC_ACCESS_TOKEN_KEY] = access_token

    if import_from_settings('OIDC_STORE_ID_TOKEN', False):
        session[OIDC_ID_TOKEN_KEY] = id_token

    if import_from_settings('OIDC_STORE_REFRESH_TOKEN', False):
        session[OIDC_REFRESH_TOKEN_KEY] = refresh_token

    expiration_interval = import_from_settings('OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS', 60 * 15)
    request.session['oidc_id_token_expiration'] = time() + expiration_interval


class AccountsOIDCBackend(OIDCAuthenticationBackend):
    """User authentication middleware for OIDC

    This is our slightly customized mozilla-django-oidc middleware used to create/update/authenticate users
    against oidc flows.
    """

    def get_user(self, user_id):
        """Retrieve the user from OIDC get_user and additionally check if they're active.
        Fixes https://github.com/mozilla/mozilla-django-oidc/issues/520
        """
        user: Optional[User] = super().get_user(user_id)
        return user if self.user_can_authenticate(user) else None

    def _check_allow_list(self, claims: dict):
        email = claims.get('email', '')
        email_verified = claims.get('email_verified')

        # Ignore allow list for services admin
        is_services_admin: bool = claims.get('is_services_admin', 'no') == 'yes'
        if is_services_admin:
            return True

        if not email_verified or not is_email_in_allow_list(email):
            logging.warning(f"Denied user {email} as they're not in the allow list.")
            messages.error(
                self.request,
                _('You are not on the allow list. If you think this is a mistake, please contact support.'),
            )
            raise PermissionDenied()

        return True

    def _set_user_fields(self, user: User, claims: dict):
        # Standard OpenID connect fields
        user.oidc_id = claims.get('sub')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.timezone = claims.get('zoneinfo', 'UTC')
        user.avatar_url = claims.get('picture')
        user.display_name = claims.get('preferred_username')
        user.username = claims.get('preferred_username')

        # Non-standard, only adjust the value if it comes not undefined / null
        is_services_admin = claims.get('is_services_admin')
        if is_services_admin is not None:
            user.is_staff = is_services_admin == 'yes'
            user.is_superuser = is_services_admin == 'yes'

        return user

    def create_user(self, claims):
        self._check_allow_list(claims)

        user = super().create_user(claims)
        user = self._set_user_fields(user, claims)
        user.save()

        # Refresh so we have access to the uuid
        user.refresh_from_db()

        return user

    def update_user(self, user, claims):
        if not user.is_active:
            self._check_allow_list(claims)

        user = self._set_user_fields(user, claims)

        # Update the email if it has changed
        user.last_used_email = user.email
        if claims.get('email') and user.email != claims.get('email'):
            user.email = claims.get('email')
        user.save()

        return user

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified oidc_id."""
        sub = claims.get('sub')
        if not sub:
            return self.UserModel.objects.none()

        user_query = self.UserModel.objects.filter(oidc_id__iexact=sub)

        # Fallback to matching by email if the env is set
        if settings.OIDC_FALLBACK_MATCH_BY_EMAIL:
            if len(user_query) == 0:
                user_query = self.UserModel.objects.filter(email__iexact=claims.get('email')).order_by('created_at')

                # Remove any weird duplicate accounts
                # See issue #236 for context
                if len(user_query) > 1:
                    to_remove = user_query[1:]
                    logging.warning(
                        f'[AccountsOIDCBackend.filter_users_by_claims] Deleting {len(to_remove)} duplicate accounts!'
                    )
                    for user in to_remove:
                        user.delete()

                # Select the first account
                user_query = user_query[:1]
        return user_query

    def authenticate(self, request, **kwargs):
        """Authenticates a user based on the OIDC code flow.
        Note: This is mostly a copy & paste from the middleware to accomondate refresh tokens.
        See https://github.com/thunderbird/thunderbird-accounts/issues/498 for more information"""

        self.request = request
        if not self.request:
            return None

        state = self.request.GET.get('state')
        code = self.request.GET.get('code')
        nonce = kwargs.pop('nonce', None)
        code_verifier = kwargs.pop('code_verifier', None)

        if not code or not state:
            return None

        reverse_url = self.get_settings('OIDC_AUTHENTICATION_CALLBACK_URL', 'oidc_authentication_callback')

        token_payload = {
            'client_id': self.OIDC_RP_CLIENT_ID,
            'client_secret': self.OIDC_RP_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': absolutify(self.request, reverse(reverse_url)),
        }

        # Send code_verifier with token request if using PKCE
        if code_verifier is not None:
            token_payload.update({'code_verifier': code_verifier})

        # Get the token
        token_info = self.get_token(token_payload)
        id_token = token_info.get('id_token')
        access_token = token_info.get('access_token')
        # New for #498
        refresh_token = token_info.get('refresh_token')

        # Validate the token
        payload = self.verify_token(id_token, nonce=nonce)

        if payload:
            # New for #498
            store_tokens(self.request, access_token, id_token, refresh_token)

            try:
                return self.get_or_create_user(access_token, id_token, payload)
            except SuspiciousOperation as exc:
                logging.warning('failed to get or create user: %s', exc)
                return None

        return None


class OIDCRefreshSession(SessionRefresh):
    """
    A middleware that will refresh the access token following proper OIDC protocol:
    https://auth0.com/docs/tokens/refresh-token/current

    Code is based on https://github.com/mozilla/mozilla-django-oidc/pull/377
    """

    def is_refreshable_url(self, request):
        """Is the session refreshable, and do we have a refresh token?"""
        is_refreshable = super().is_refreshable_url(request)
        return is_refreshable and request.session.get(OIDC_REFRESH_TOKEN_KEY)

    def is_expired(self, request):
        expiration = request.session.get('oidc_id_token_expiration', 0)
        now = time()
        return expiration > 0 and now >= expiration

    def process_request(self, request):
        """Handle a refresh session request. If it's not refreshable or the token expired then we skip this
        and deal with the consequences elsewhere"""
        if not self.is_refreshable_url(request):
            logging.debug('request is not refreshable')
            return

        if not self.is_expired(request):
            logging.debug('request has expired')
            return

        token_url = import_from_settings('OIDC_OP_TOKEN_ENDPOINT')
        client_id = import_from_settings('OIDC_RP_CLIENT_ID')
        client_secret = import_from_settings('OIDC_RP_CLIENT_SECRET')
        refresh_token = request.session.get(OIDC_REFRESH_TOKEN_KEY)

        if not refresh_token:
            logging.debug('no refresh token stored')
            return self.finish(request, prompt_reauth=True)

        token_payload = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
        }

        req_auth = None
        if self.get_settings('OIDC_TOKEN_USE_BASIC_AUTH', False):
            # When Basic auth is defined, create the Auth Header and remove secret from payload.
            user = token_payload.get('client_id')
            pw = token_payload.get('client_secret')

            req_auth = HTTPBasicAuth(user, pw)
            del token_payload['client_secret']

        try:
            response = requests.post(
                token_url, auth=req_auth, data=token_payload, verify=import_from_settings('OIDC_VERIFY_SSL', True)
            )
            response.raise_for_status()
            token_info = response.json()
        except requests.exceptions.Timeout:
            logging.debug('timed out refreshing access token')
            # Don't prompt for reauth as this could be a temporary problem
            return self.finish(request, prompt_reauth=False)
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code
            logging.debug('http error %s when refreshing access token', status_code)
            # OAuth error response will be a 400 for various situations, including
            # an expired token. https://datatracker.ietf.org/doc/html/rfc6749#section-5.2
            return self.finish(request, prompt_reauth=(status_code == 400))
        except JSONDecodeError:
            logging.debug('malformed response when refreshing access token')
            # Don't prompt for reauth as this could be a temporary problem
            return self.finish(request, prompt_reauth=False)
        except Exception as exc:
            logging.debug('unknown error occurred when refreshing access token: %s', exc)
            # Don't prompt for reauth as this could be a temporary problem
            return self.finish(request, prompt_reauth=False)

        # Until we can properly validate an ID token on the refresh response
        # per the spec[1], we intentionally drop the id_token.
        # [1]: https://openid.net/specs/openid-connect-core-1_0.html#RefreshTokenResponse
        id_token = None
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        store_tokens(request, access_token, id_token, refresh_token)

    def finish(self, request, prompt_reauth=True):
        """Finish request handling and handle sending downstream responses for XHR.

        This function should only be run if the session is determind to
        be expired.

        Almost all XHR request handling in client-side code struggles
        with redirects since redirecting to a page where the user
        is supposed to do something is extremely unlikely to work
        in an XHR request. Make a special response for these kinds
        of requests.

        The use of 403 Forbidden is to match the fact that this
        middleware doesn't really want the user in if they don't
        refresh their session.
        """
        default_response = None
        xhr_response_json = {'error': 'the authentication session has expired'}
        if prompt_reauth:
            # The id_token has expired, so we have to re-authenticate silently.
            refresh_url = self._prepare_reauthorization(request)
            default_response = HttpResponseRedirect(refresh_url)
            xhr_response_json['refresh_url'] = refresh_url

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            xhr_response = JsonResponse(xhr_response_json, status=403)
            if 'refresh_url' in xhr_response_json:
                xhr_response['refresh_url'] = xhr_response_json['refresh_url']
            return xhr_response
        else:
            return default_response

    def _prepare_reauthorization(self, request):
        # Constructs a new authorization grant request to refresh the session.
        # Besides constructing the request, the state and nonce included in the
        # request are registered in the current session in preparation for the
        # client following through with the authorization flow.
        auth_url = self.OIDC_OP_AUTHORIZATION_ENDPOINT
        client_id = self.OIDC_RP_CLIENT_ID
        state = get_random_string(self.OIDC_STATE_SIZE)

        # Build the parameters as if we were doing a real auth handoff, except
        # we also include prompt=none.
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': absolutify(request, reverse(self.OIDC_AUTHENTICATION_CALLBACK_URL)),
            'state': state,
            'scope': self.OIDC_RP_SCOPES,
            'prompt': 'none',
        }

        params.update(self.get_settings('OIDC_AUTH_REQUEST_EXTRA_PARAMS', {}))

        if self.OIDC_USE_NONCE:
            nonce = get_random_string(self.OIDC_NONCE_SIZE)
            params.update({'nonce': nonce})

        if self.get_settings('OIDC_USE_PKCE', False):
            code_verifier_length = self.get_settings('OIDC_PKCE_CODE_VERIFIER_SIZE', 64)
            # Check that code_verifier_length is between the min and max length
            # defined in https://datatracker.ietf.org/doc/html/rfc7636#section-4.1
            if not (43 <= code_verifier_length <= 128):
                raise ValueError('code_verifier_length must be between 43 and 128')

            # Generate code_verifier and code_challenge pair
            code_verifier = get_random_string(code_verifier_length)
            code_challenge_method = self.get_settings('OIDC_PKCE_CODE_CHALLENGE_METHOD', 'S256')
            code_challenge = generate_code_challenge(code_verifier, code_challenge_method)

            # Append code_challenge to authentication request parameters
            params.update(
                {
                    'code_challenge': code_challenge,
                    'code_challenge_method': code_challenge_method,
                }
            )
        else:
            code_verifier = None

        add_state_and_verifier_and_nonce_to_session(request, state, params, code_verifier)

        request.session['oidc_login_next'] = request.get_full_path()

        query = urlencode(params, quote_via=quote)
        return '{auth_url}?{query}'.format(auth_url=auth_url, query=query)


class SetHostIPInAllowedHostsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        allowed_hosts = settings.ALLOWED_HOSTS

        # Get the IP of whatever machine is running this code and allow it as a hostname
        hostname = gethostbyname(gethostname())
        if hostname not in allowed_hosts:
            allowed_hosts.append(hostname)

        # Set both django allowed hosts and cors allowed origins
        settings.ALLOWED_HOSTS = allowed_hosts

        response = self.get_response(request)

        return response

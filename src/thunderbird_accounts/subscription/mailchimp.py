import base64
import hashlib
import logging

import requests
import sentry_sdk
from django.conf import settings
from requests.exceptions import JSONDecodeError

from thunderbird_accounts.celery.exceptions import TaskFailed


def _get_response_error_details(ex: requests.exceptions.RequestException) -> dict:
    try:
        return ex.response.json() if ex.response is not None else {}
    except (JSONDecodeError, AttributeError):
        return {}


def _get_response_status_code(ex: requests.exceptions.RequestException) -> int | None:
    return ex.response.status_code if ex.response is not None else None


class MailchimpClient:
    """Thin client for the Mailchimp Marketing API v3 list endpoints."""

    def __init__(self):
        self._basic_auth = base64.b64encode(
            f'this_does_not_support_bearer_auth:{settings.MAILCHIMP_API_KEY}'.encode()
        ).decode()

    @staticmethod
    def _hash_email(email: str) -> str:
        md5_hasher = hashlib.new('md5')
        md5_hasher.update(email.lower().encode())
        return md5_hasher.hexdigest()

    def _api_query(self, method: str, api_endpoint: str, data: dict | None = None) -> requests.Response:
        """Execute a request against the Mailchimp list API."""
        api_url = f'https://{settings.MAILCHIMP_DC}.api.mailchimp.com/3.0/lists/{settings.MAILCHIMP_LIST_ID}'
        response: requests.Response = requests.request(
            method=method.upper(),
            url=f'{api_url}{api_endpoint}',
            headers={'Authorization': f'Basic {self._basic_auth}'},
            json=data,
        )
        response.raise_for_status()
        return response

    def add_or_tag_member(
        self,
        email: str,
        tag: str,
        *,
        language: str,
        error_context: dict | None = None,
    ) -> None:
        """Add a list member or apply a tag if they are already subscribed."""
        hashed_email = self._hash_email(email)

        # Check if the user is on the list, and if they are then update their tags array with our new one.
        try:
            response = self._api_query('get', f'/members/{hashed_email}')

            data = response.json() or {}
            tags = {t.get('name'): True for t in data.get('tags', [])}

            # They're already in the mailing list with the assigned tag, so don't do anything.
            if tags.get(tag):
                return

            self._api_query(
                'post',
                f'/members/{hashed_email}/tags',
                data={'tags': [{'name': tag, 'status': 'active'}]},
            )
            return

        except requests.exceptions.RequestException as ex:
            # Something error'd out, we won't capture this just yet but we should add the context
            # in case the next request fails.

            # Error details reference: https://mailchimp.com/developer/marketing/docs/errors/#error-glossary
            error_details = _get_response_error_details(ex)
            sentry_sdk.set_context('mailchimp_tag_error', error_details)

        # Try to create the user with the tag we want
        try:
            self._api_query(
                'post',
                '/members',
                data={
                    'email_address': email,
                    'status': 'subscribed',
                    'email_type': 'html',
                    'language': language,
                    'tags': [tag],
                },
            )
        except requests.exceptions.RequestException as ex:
            # Error details reference: https://mailchimp.com/developer/marketing/docs/errors/#error-glossary
            error_details = _get_response_error_details(ex)
            sentry_sdk.set_context('mailchimp_error', error_details)
            sentry_sdk.capture_exception(ex)

            raise TaskFailed(
                'mailchimp error',
                {
                    **(error_context or {}),
                    'error_msg_title': error_details.get('title', 'N/A'),
                    'error_msg_detail': error_details.get('detail', 'N/A'),
                    'error_msg_type': error_details.get('type', 'N/A'),
                    'error_status_code': _get_response_status_code(ex),
                },
            )

    def remove_tag_from_member(
        self,
        email: str,
        tag: str,
        *,
        error_context: dict | None = None,
    ) -> None:
        """Remove a tag from an existing list member.

        Best-effort: silently returns if the member does not exist or the tag is not
        present. Errors during the remove request are logged and captured in Sentry
        but never raised so that callers are not blocked by cleanup failures.
        """
        hashed_email = self._hash_email(email)

        try:
            response = self._api_query('get', f'/members/{hashed_email}')
            data = response.json() or {}
            tags = {t.get('name'): True for t in data.get('tags', [])}

            if not tags.get(tag):
                return

        except requests.exceptions.RequestException:
            # Member does not exist or GET failed — nothing to remove.
            return

        try:
            self._api_query(
                'post',
                f'/members/{hashed_email}/tags',
                data={'tags': [{'name': tag, 'status': 'inactive'}]},
            )
        except requests.exceptions.RequestException as ex:
            try:
                error_details = ex.response.json()
            except (JSONDecodeError, AttributeError):
                error_details = {}

            sentry_sdk.set_context('mailchimp_remove_tag_error', {**(error_context or {}), **error_details})
            sentry_sdk.capture_exception(ex)
            logging.warning(f'MailchimpClient.remove_tag_from_member: failed to remove tag "{tag}" from {email}: {ex}')

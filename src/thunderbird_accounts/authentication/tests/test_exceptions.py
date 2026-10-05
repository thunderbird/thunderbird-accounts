import requests
from django.test import SimpleTestCase

from thunderbird_accounts.authentication.exceptions import ImportUserError


class ImportUserErrorTestCase(SimpleTestCase):
    def test_keycloak_profile_validation_failure_is_validation_error(self):
        """Keycloak rejects names and usernames with disallowed characters as a 400 user profile validation error."""
        bodies = [
            b'{"field":"firstName","errorMessage":"error-person-name-invalid-character","params":["firstName"]}',
            b'{"field":"username","errorMessage":"error-username-invalid-character","params":["username"]}',
        ]
        for body in bodies:
            with self.subTest(body=body):
                response = requests.Response()
                response.status_code = 400
                response._content = body

                error = ImportUserError.from_request_exception(requests.HTTPError(response=response))

                self.assertTrue(error.is_validation_error)
                self.assertFalse(error.is_already_exists)

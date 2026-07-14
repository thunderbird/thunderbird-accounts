from django.test import SimpleTestCase

from thunderbird_accounts.core.validators import normalize_custom_domain


class CustomDomainValidationTestCase(SimpleTestCase):
    def test_normalizes_domain_before_validation(self):
        cases = {
            'Example.COM': 'example.com',
            ' example . com ': 'example.com',
            ' BÜCHER.example ': 'bücher.example',
        }

        for domain_name, expected in cases.items():
            with self.subTest(domain_name=domain_name):
                self.assertEqual(expected, normalize_custom_domain(domain_name))

    def test_rejects_missing_and_trailing_dot_values(self):
        for domain_name in [
            None,
            '',
            'example.',
        ]:
            with self.subTest(domain_name=domain_name):
                self.assertIsNone(normalize_custom_domain(domain_name))

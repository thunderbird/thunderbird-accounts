
from django.test import TestCase


from thunderbird_accounts.authentication.reserved import is_reserved, servers, support

class IsReservedUnitTests(TestCase):
    def test_brand_names(self):
        for brand in ['thunderbird', 'mozilla', 'firefox', 'help', 'support', 'mzla']:
            self.assertTrue(is_reserved(brand))

    def test_brand_plus_variants(self):
        # (brands)? allows more than one match
        for name in ['thunderbirdthunderbird', 'supportsupport']:
            self.assertFalse(is_reserved(name))

    def test_brand_support_help_suffix_patterns(self):
        # ^(brand).*support?$ and customer_support and help
        for name in [
            'thunderbirdpro_customer_support',
            'thunderbirdpro_support',
            'thunderbird_customer_support',
            'thunderbird_support',
            'thunderbird-support',
            'mzla_support',
            'mzla_help',
            'mozilla_support',
            'firefox_help',
        ]:
            self.assertTrue(is_reserved(name))

        # ^(brand).*email?$ and ^(brand).*org?$
        for name in ['thunderbird_email', 'firefox_org']:
            self.assertTrue(is_reserved(name), name)

    def test_official_and_real_variants(self):
        for name in [
            'official_thunderbird',
            'officialsupport',
            'realmozilla',
            'firefox_real',
            'support_official',
            'mozilla_real',
        ]:
            self.assertTrue(is_reserved(name))

    def test_mzla_test_variants(self):
        for name in ['mzla-test', 'mzla-test.123', 'mzla-test.alpha.beta']:
            self.assertTrue(is_reserved(name))

    def test_common_example_usernames(self):
        for name in ['username', 'user_name', 'user', 'exampleuser', 'example_name', 'example-user', 'test']:
            self.assertTrue(is_reserved(name))

    def test_servers(self):
        for name in ['admin', 'root', 'webmaster', 'postmaster', 'superuser', 'administrator']:
            self.assertTrue(is_reserved(name))

    def test_team_and_contact(self):
        for name in [
            'team',
            'hr',
            'accounts_team',
            'engineering',
            'engineering_team',
            'marketing_team',
            'design',
            'design_team',
            'contactus',
            'contact_us',
        ]:
            self.assertTrue(is_reserved(name))

    def test_internal_names(self):
        # select a few to hardcode test
        for name in ['root', 'postmaster', 'support', 'marketing']:
            self.assertTrue(is_reserved(name), name)

        for name in servers + support:
            self.assertTrue(is_reserved(name), name)

    def test_birbs(self):
        for name in ['roc', 'ezio', 'mithu', 'ava', 'callum', 'sora', 'robin', 'nemo']:
            self.assertTrue(is_reserved(name))

    def test_non_reserved(self):
        reserved_names_related = ['mozillafan', 'supporter', 'helper', 'hostmastery', 'contacts']
        unrelated = ['randomuser', 'this_should_not_be_a_problem', '123_asdf', 'asdf_123', '123asdf', 'asdf123']
        for name in reserved_names_related + unrelated:
            self.assertFalse(is_reserved(name))

    def test_partial_matches_should_pass(self):
        # Anchors ^...$ mean full-string match only
        for name in ['user123', 'myusernamex', 'rooted', 'teamwork', 'contacting']:
            self.assertFalse(is_reserved(name))

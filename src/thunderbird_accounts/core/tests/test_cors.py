from django.test import Client as RequestClient, SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(CORS_ALLOWED_ORIGINS=[], ZENDESK_SUBDOMAIN='example')
class ZendeskSidebarCorsTestCase(SimpleTestCase):
    def setUp(self):
        self.client = RequestClient()

    def options(self, url, origin):
        return self.client.options(
            url,
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization, content-type',
        )

    def test_zendesk_origin_is_allowed_for_sidebar_customer_api(self):
        response = self.options(reverse('api_zendesk_sidebar_customer'), 'https://example.zendesk.com')

        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'https://example.zendesk.com')

    def test_zendesk_origin_is_not_allowed_for_unrelated_api(self):
        response = self.options(reverse('legal_current'), 'https://example.zendesk.com')

        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_other_origin_is_not_allowed_for_sidebar_customer_api(self):
        response = self.options(reverse('api_zendesk_sidebar_customer'), 'https://attacker.example')

        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

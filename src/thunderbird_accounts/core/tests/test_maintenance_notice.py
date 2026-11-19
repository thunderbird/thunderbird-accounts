import json
from unittest.mock import patch

import requests
from django.conf import settings
from django.core.cache import cache
from django.test import Client as RequestClient, TestCase, override_settings
from django.utils.html import strip_tags

from thunderbird_accounts.core.maintenance_notice import get_maintenance_notice

KEYCLOAK_API_ENDPOINT = 'http://keycloak.test/admin/realms/tbpro/'


@override_settings(KEYCLOAK_API_ENDPOINT=KEYCLOAK_API_ENDPOINT)
@patch('thunderbird_accounts.core.maintenance_notice.KeycloakClient')
class GetMaintenanceNoticeTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def _set_overrides(self, mock_client_cls, overrides):
        mock_client_cls.return_value.request.return_value.json.return_value = overrides

    def test_returns_the_notice_from_the_realm_overrides(self, mock_client_cls):
        self._set_overrides(
            mock_client_cls,
            {
                'maintenanceNotice': '  Thundermail is down for maintenance.  ',
                'maintenanceNoticeType': 'critical',
                'maintenanceNoticeStatusUrl': ' https://status.example.org/ ',
                'maintenanceNoticeStatusText': 'Status page',
                'unrelatedKey': 'ignored',
            },
        )

        self.assertEqual(
            get_maintenance_notice(),
            {
                'text': 'Thundermail is down for maintenance.',
                'type': 'critical',
                'statusUrl': 'https://status.example.org/',
                'statusText': 'Status page',
            },
        )
        mock_client_cls.return_value.request.assert_called_once_with(
            'localization/en', timeout=settings.MAINTENANCE_NOTICE_TIMEOUT_SECONDS
        )

    def test_returns_none_without_notice_text(self, mock_client_cls):
        for overrides in ({}, {'maintenanceNotice': '   '}, {'maintenanceNoticeType': 'critical'}):
            with self.subTest(overrides=overrides):
                cache.clear()
                self._set_overrides(mock_client_cls, overrides)
                self.assertIsNone(get_maintenance_notice())

    def test_unknown_type_falls_back_to_warning(self, mock_client_cls):
        for notice_type in (None, '', 'success', 'Critical', ' critical'):
            with self.subTest(notice_type=notice_type):
                cache.clear()
                self._set_overrides(
                    mock_client_cls, {'maintenanceNotice': 'Maintenance', 'maintenanceNoticeType': notice_type}
                )
                self.assertEqual(get_maintenance_notice()['type'], 'warning')

    def test_drops_status_urls_that_are_not_http(self, mock_client_cls):
        for status_url in ('javascript:alert(1)', 'ftp://status.example.org/', 'status.example.org', '', None):
            with self.subTest(status_url=status_url):
                cache.clear()
                self._set_overrides(
                    mock_client_cls, {'maintenanceNotice': 'Maintenance', 'maintenanceNoticeStatusUrl': status_url}
                )
                self.assertIsNone(get_maintenance_notice()['statusUrl'])

    def test_blank_status_text_is_left_to_the_frontend_default(self, mock_client_cls):
        self._set_overrides(mock_client_cls, {'maintenanceNotice': 'Maintenance', 'maintenanceNoticeStatusText': ' '})

        self.assertIsNone(get_maintenance_notice()['statusText'])

    def test_caches_the_notice(self, mock_client_cls):
        self._set_overrides(mock_client_cls, {'maintenanceNotice': 'Maintenance'})

        first = get_maintenance_notice()
        self._set_overrides(mock_client_cls, {'maintenanceNotice': 'Changed'})

        self.assertEqual(get_maintenance_notice(), first)
        self.assertEqual(mock_client_cls.return_value.request.call_count, 1)

    def test_caches_the_absence_of_a_notice(self, mock_client_cls):
        self._set_overrides(mock_client_cls, {})

        self.assertIsNone(get_maintenance_notice())
        self.assertIsNone(get_maintenance_notice())
        self.assertEqual(mock_client_cls.return_value.request.call_count, 1)

    def test_read_failures_show_no_notice_and_are_cached(self, mock_client_cls):
        for error in (requests.ConnectionError('down'), requests.HTTPError('403'), ValueError('bad json'), KeyError()):
            with self.subTest(error=error):
                cache.clear()
                mock_client_cls.return_value.request.reset_mock()
                mock_client_cls.return_value.request.side_effect = error

                with self.assertLogs('thunderbird_accounts.core.maintenance_notice', 'WARNING'):
                    self.assertIsNone(get_maintenance_notice())
                self.assertIsNone(get_maintenance_notice())
                self.assertEqual(mock_client_cls.return_value.request.call_count, 1)

    def test_non_object_response_shows_no_notice(self, mock_client_cls):
        self._set_overrides(mock_client_cls, ['maintenanceNotice'])

        with self.assertLogs('thunderbird_accounts.core.maintenance_notice', 'WARNING'):
            self.assertIsNone(get_maintenance_notice())

    @override_settings(KEYCLOAK_API_ENDPOINT=None)
    def test_skips_keycloak_when_the_admin_api_is_not_configured(self, mock_client_cls):
        self.assertIsNone(get_maintenance_notice())
        mock_client_cls.assert_not_called()


class MaintenanceNoticePageDataTestCase(TestCase):
    @patch('thunderbird_accounts.core.views.get_maintenance_notice')
    def test_page_data_includes_the_notice(self, mock_get_notice):
        notice = {'text': 'Maintenance', 'type': 'info', 'statusUrl': None, 'statusText': None}
        mock_get_notice.return_value = notice

        response = RequestClient().get('/contact')

        page_data = json.loads(strip_tags(response.context['page_load_data_script']))
        self.assertEqual(page_data['maintenanceNotice'], notice)

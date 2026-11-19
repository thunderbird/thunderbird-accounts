import json
from unittest.mock import patch

import requests
from django.conf import settings
from django.core.cache import cache
from django.test import Client as RequestClient, TestCase, override_settings
from django.utils.html import strip_tags

from thunderbird_accounts.core.maintenance_notice import get_maintenance_notice


@override_settings(KEYCLOAK_API_ENDPOINT='http://keycloak.test/admin/realms/tbpro/')
@patch('thunderbird_accounts.core.maintenance_notice.KeycloakClient')
class GetMaintenanceNoticeTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def _set_overrides(self, mock_client_cls, overrides):
        cache.clear()
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
        for overrides in ({}, {'maintenanceNotice': '   '}):
            with self.subTest(overrides=overrides):
                self._set_overrides(mock_client_cls, overrides)
                self.assertIsNone(get_maintenance_notice())

    def test_unknown_type_falls_back_to_warning(self, mock_client_cls):
        for notice_type in (None, 'success', 'Critical'):
            with self.subTest(notice_type=notice_type):
                self._set_overrides(
                    mock_client_cls, {'maintenanceNotice': 'Maintenance', 'maintenanceNoticeType': notice_type}
                )
                self.assertEqual(get_maintenance_notice()['type'], 'warning')

    def test_only_links_http_status_urls(self, mock_client_cls):
        for status_url in ('javascript:alert(1)', 'status.example.org', ''):
            with self.subTest(status_url=status_url):
                self._set_overrides(
                    mock_client_cls, {'maintenanceNotice': 'Maintenance', 'maintenanceNoticeStatusUrl': status_url}
                )
                self.assertIsNone(get_maintenance_notice()['statusUrl'])

    def test_caches_the_notice(self, mock_client_cls):
        self._set_overrides(mock_client_cls, {'maintenanceNotice': 'Maintenance'})

        first = get_maintenance_notice()
        mock_client_cls.return_value.request.return_value.json.return_value = {'maintenanceNotice': 'Changed'}

        self.assertEqual(get_maintenance_notice(), first)
        self.assertEqual(mock_client_cls.return_value.request.call_count, 1)

    def test_unreadable_overrides_show_no_notice_and_are_cached(self, mock_client_cls):
        mock_request = mock_client_cls.return_value.request
        cases = {
            'timeout': {'side_effect': requests.Timeout('timed out')},
            'invalid JSON': {'side_effect': ValueError('bad json')},
            'token response without access_token': {'side_effect': KeyError('access_token')},
            'non-object JSON': {'json': ['maintenanceNotice']},
        }
        for case, setup in cases.items():
            with self.subTest(case=case):
                self._set_overrides(mock_client_cls, setup.get('json'))
                mock_request.reset_mock()
                mock_request.side_effect = setup.get('side_effect')

                with self.assertLogs('thunderbird_accounts.core.maintenance_notice', 'WARNING'):
                    self.assertIsNone(get_maintenance_notice())
                self.assertIsNone(get_maintenance_notice())
                self.assertEqual(mock_request.call_count, 1)


class MaintenanceNoticePageDataTestCase(TestCase):
    @patch('thunderbird_accounts.core.views.get_maintenance_notice')
    def test_page_data_includes_the_notice(self, mock_get_notice):
        notice = {'text': 'Maintenance', 'type': 'info', 'statusUrl': None, 'statusText': None}
        mock_get_notice.return_value = notice

        response = RequestClient().get('/contact')

        page_data = json.loads(strip_tags(response.context['page_load_data_script']))
        self.assertEqual(page_data['maintenanceNotice'], notice)

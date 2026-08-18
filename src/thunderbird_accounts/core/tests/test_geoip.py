from pathlib import Path
from unittest.mock import patch

import maxminddb
from django.test import TestCase

from thunderbird_accounts.core.geoip import enrich_sessions_with_geoip, lookup_ip_location


class GeoIPLookupTestCase(TestCase):
    @patch('thunderbird_accounts.core.geoip.maxminddb.open_database')
    @patch('thunderbird_accounts.core.geoip.Path.exists', return_value=True)
    def test_lookup_ip_location_returns_mmdb_match(self, _mock_exists, mock_open_database):
        mock_reader = mock_open_database.return_value.__enter__.return_value
        mock_reader.get.return_value = {
            'city': {'names': {'en': 'Mountain View'}},
            'subdivisions': [{'names': {'en': 'California'}}],
            'country': {'iso_code': 'US'},
            'continent': {'code': 'NA'},
        }

        self.assertEqual(
            lookup_ip_location('203.0.113.10'),
            {
                'city': 'Mountain View',
                'state': 'California',
                'country_code': 'US',
                'continent': 'NA',
            },
        )
        mock_open_database.assert_called_once_with(Path('/app/data/dbip-city-lite.mmdb'))
        mock_reader.get.assert_called_once_with('203.0.113.10')

    @patch('thunderbird_accounts.core.geoip.maxminddb.open_database')
    @patch('thunderbird_accounts.core.geoip.Path.exists', return_value=True)
    def test_lookup_ip_location_returns_none_for_unknown_ip(self, _mock_exists, mock_open_database):
        mock_reader = mock_open_database.return_value.__enter__.return_value
        mock_reader.get.return_value = None

        self.assertIsNone(lookup_ip_location('203.0.113.20'))

    def test_lookup_ip_location_returns_none_when_mmdb_is_missing(self):
        self.assertIsNone(lookup_ip_location('203.0.113.20'))

    @patch('thunderbird_accounts.core.geoip.maxminddb.open_database')
    @patch('thunderbird_accounts.core.geoip.Path.exists', return_value=True)
    @patch('thunderbird_accounts.core.geoip.logger')
    def test_lookup_ip_location_returns_none_when_mmdb_is_invalid(self, mock_logger, _mock_exists, mock_open_database):
        mock_open_database.side_effect = maxminddb.InvalidDatabaseError('bad mmdb')

        self.assertIsNone(lookup_ip_location('203.0.113.20'))
        mock_logger.exception.assert_called_once()

    def test_enrich_sessions_with_geoip_uses_null_for_unknown_location(self):
        sessions = [{'id': 'session-id', 'ip_address': '203.0.113.10'}]

        self.assertEqual(
            enrich_sessions_with_geoip(sessions),
            [{'id': 'session-id', 'ip_address': '203.0.113.10', 'location': None}],
        )

    @patch('thunderbird_accounts.core.geoip.lookup_ip_location')
    def test_enrich_sessions_with_geoip_skips_missing_ip(self, mock_lookup_ip_location):
        sessions = [{'client_id': 'thunderbird-desktop'}]

        self.assertEqual(
            enrich_sessions_with_geoip(sessions),
            [{'client_id': 'thunderbird-desktop', 'location': None}],
        )
        mock_lookup_ip_location.assert_not_called()

    @patch('thunderbird_accounts.core.geoip.lookup_ip_location')
    def test_enrich_sessions_with_geoip_reuses_lookup_for_matching_ips(self, mock_lookup_ip_location):
        mock_lookup_ip_location.return_value = {'city': 'Mountain View'}
        sessions = [
            {'id': 'first-session', 'ip_address': '203.0.113.10'},
            {'id': 'second-session', 'ip_address': '203.0.113.10'},
        ]

        self.assertEqual(
            enrich_sessions_with_geoip(sessions),
            [
                {'id': 'first-session', 'ip_address': '203.0.113.10', 'location': {'city': 'Mountain View'}},
                {'id': 'second-session', 'ip_address': '203.0.113.10', 'location': {'city': 'Mountain View'}},
            ],
        )
        mock_lookup_ip_location.assert_called_once_with('203.0.113.10')

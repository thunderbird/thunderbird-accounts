# Manage mapping IPs to place names
import logging
from pathlib import Path
from typing import TypeVar

import maxminddb

from thunderbird_accounts.core.types import GeoIPLocation, GeoIPSession

logger = logging.getLogger(__name__)

GeoIPSessionT = TypeVar('GeoIPSessionT', bound=GeoIPSession)

# Expected to be provided by the container built by Dockerfile
GEOIP_CITY_MMDB_PATH = Path('/app/data/dbip-city-lite.mmdb')


def lookup_ip_location(ip_address: str) -> GeoIPLocation | None:
    """Given IP address, return a location string to represent it."""
    if not GEOIP_CITY_MMDB_PATH.exists():
        return None

    try:
        with maxminddb.open_database(GEOIP_CITY_MMDB_PATH) as reader:
            location = reader.get(ip_address)
    except (OSError, ValueError, maxminddb.InvalidDatabaseError):
        logger.exception('Could not look up GeoIP location for %s', ip_address)
        return None

    if not location:
        return None

    city = location.get('city') or {}
    subdivision = next(iter(location.get('subdivisions') or []), {})
    country = location.get('country') or {}
    continent = location.get('continent') or {}

    return {
        'city': (city.get('names') or {}).get('en') or city.get('name'),
        'state': (subdivision.get('names') or {}).get('en') or subdivision.get('name'),
        'country_code': country.get('iso_code'),
        'continent': continent.get('code'),
    }

def enrich_sessions_with_geoip(sessions: list[GeoIPSessionT]) -> list[GeoIPSessionT]:
    """Add human-friendly locations based on IP address"""
    locations_by_ip: dict[str, GeoIPLocation | None] = {}
    for session in sessions:
        ip_address = session.get('ip_address')
        if not ip_address:
            session['location'] = None
            continue
        if ip_address not in locations_by_ip:
            locations_by_ip[ip_address] = lookup_ip_location(ip_address)
        session['location'] = locations_by_ip[ip_address]
    return sessions

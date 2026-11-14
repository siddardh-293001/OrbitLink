"""CelesTrak JSON mean elements; never substitutes synthetic data for a failed feed."""
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from orbitlink.orbit.tle import TLERecord, parse_tle_catalog

GROUPS = {"Starlink": "starlink", "Iridium NEXT": "iridium-NEXT"}

@dataclass(frozen=True)
class OMMRecord:
    name: str
    satellite_id: str
    epoch: datetime
    fields: dict
    age_days = TLERecord.age_days
    quality = TLERecord.quality


def parse_catalog(text):
    if not text.lstrip().startswith('['):
        return parse_tle_catalog(text)
    rows = json.loads(text)
    if not rows or not isinstance(rows, list):
        raise ValueError('Catalog must contain a non-empty JSON list')
    records = []
    seen = set()
    for row in rows:
        fields = dict(row)
        for key, default in [('CENTER_NAME','EARTH'),('REF_FRAME','TEME'),('TIME_SYSTEM','UTC'),('MEAN_ELEMENT_THEORY','SGP4')]:
            if fields.setdefault(key, default) != default:
                raise ValueError(f'Unsupported {key}')
        for key in ['MEAN_MOTION','ECCENTRICITY','INCLINATION','RA_OF_ASC_NODE','ARG_OF_PERICENTER','MEAN_ANOMALY','BSTAR','MEAN_MOTION_DOT','MEAN_MOTION_DDOT']:
            if not math.isfinite(float(fields[key])):
                raise ValueError(f'Invalid {key}')
        if float(fields['MEAN_MOTION']) <= 0 or not 0 <= float(fields['ECCENTRICITY']) < 1 or not 0 <= float(fields['INCLINATION']) <= 180:
            raise ValueError('Invalid orbital elements')
        identity = str(int(fields['NORAD_CAT_ID']))
        if identity in seen:
            raise ValueError('Duplicate satellite ID')
        seen.add(identity)
        epoch = datetime.fromisoformat(fields['EPOCH'].replace('Z','+00:00'))
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=timezone.utc)
        records.append(OMMRecord(fields.get('OBJECT_NAME', identity), identity, epoch, fields))
    return tuple(records)


def fetch_catalog(group):
    url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=' + GROUPS[group] + '&FORMAT=JSON'
    with urlopen(Request(url, headers={'User-Agent':'OrbitLink/0.2'}), timeout=15) as response:
        body = response.read(10_000_001)
    if len(body) > 10_000_000:
        raise ValueError('Catalog exceeds the 10 MB limit')
    parse_catalog(body.decode('utf-8-sig'))
    return body, datetime.now(timezone.utc).isoformat()


def load_catalog(group):
    """Try the network; on failure return a labeled, dated real-data snapshot."""
    from pathlib import Path
    try:
        body, retrieved = fetch_catalog(group)
        return body, retrieved, 'Downloaded from CelesTrak'
    except (OSError, ValueError, KeyError, TypeError):
        path = Path(__file__).parent / 'data' / (GROUPS[group] + '.json')
        if not path.exists():
            raise RuntimeError('The feed is unavailable and no saved catalog exists. Upload a JSON catalog.')
        snapshot = json.loads(path.read_text())
        body = json.dumps(snapshot['records']).encode()
        records = parse_catalog(body.decode())
        now = datetime.now(timezone.utc)
        if not any(0 <= (now-r.epoch).total_seconds()/86400 <= 14 for r in records):
            raise RuntimeError('The feed is unavailable and the saved catalog has expired. Upload fresh orbital data.')
        return body, snapshot['retrieved_at'], 'Saved real-data snapshot — live feed unavailable'

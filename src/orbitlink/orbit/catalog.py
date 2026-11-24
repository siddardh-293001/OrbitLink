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
    """Serve the latest validated snapshot, refreshing in the background."""
    from pathlib import Path
    import os, tempfile
    cache = Path(os.environ.get('ORBITLINK_DATA_DIR', tempfile.gettempdir())) / 'catalogs'
    candidates=[cache / (GROUPS[group]+'.json'), Path(__file__).parent / 'data' / (GROUPS[group]+'.json')]
    for path in candidates:
        try:
            snapshot=json.loads(path.read_text())
            body=json.dumps(snapshot['records']).encode()
            records=parse_catalog(body.decode())
            now=datetime.now(timezone.utc)
            if any(not r.quality(now) for r in records):
                return body,snapshot['retrieved_at'],'Validated saved catalog · automatic refresh every 6 hours'
        except (OSError,ValueError,KeyError,TypeError):
            continue
    raise RuntimeError('No usable saved orbital data. Automatic refresh is pending or failed; inspect catalog status.')


REFRESH_STATUS = {}

def refresh_catalog(group):
    """Atomically replace a snapshot only after complete validation."""
    from pathlib import Path
    import os, tempfile
    try:
        body,retrieved=fetch_catalog(group)
        records=parse_catalog(body.decode('utf-8-sig'))
        if not any(not r.quality(datetime.now(timezone.utc)) for r in records):
            raise ValueError('Downloaded catalog has no fresh records')
        cache=Path(os.environ.get('ORBITLINK_DATA_DIR',tempfile.gettempdir()))/'catalogs'
        cache.mkdir(parents=True,exist_ok=True)
        target=cache/(GROUPS[group]+'.json')
        temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(retrieved_at=retrieved,records=json.loads(body))))
        os.replace(temporary,target)
        REFRESH_STATUS[group]=dict(ok=True,checked_at=retrieved,records=len(records))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        REFRESH_STATUS[group]=dict(ok=False,checked_at=datetime.now(timezone.utc).isoformat(),error=str(exc))

def start_catalog_refresh():
    import threading
    def worker():
        import time
        while True:
            for group in GROUPS:refresh_catalog(group)
            time.sleep(6*3600)
    threading.Thread(target=worker,daemon=True,name='catalog-refresh').start()

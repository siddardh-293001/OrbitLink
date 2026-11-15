"""React mission control host; shares the existing Python simulation engine."""
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from orbitlink.orbit.catalog import load_catalog, parse_catalog
from orbitlink.analytics.simulator import run_tle_simulation
from orbitlink.core.models import GroundSite
from orbitlink.core.constants import EARTH_RADIUS_M

ROOT = Path(__file__).resolve().parents[3]

@lru_cache(maxsize=6)
def scenario(group, count, lat, lon, minute):
    body, retrieved, source = load_catalog(group)
    now = datetime.fromtimestamp(minute*60, timezone.utc)
    all_records = parse_catalog(body.decode())
    records = sorted((r for r in all_records if not r.quality(now)),key=lambda r:r.epoch,reverse=True)
    if count:
        records = records[:count]
    if not records:
        raise ValueError('No fresh orbital records. Update the saved catalog.')
    result = run_tle_simulation(records,start_time_utc=now,site=GroundSite('Terminal',lat,lon),duration_seconds=1800,timestep_seconds=300 if count == 0 else 60)
    return dict(source=source,retrieved=retrieved,start=now.isoformat(),total=len(all_records),names={r.satellite_id:r.name for r in records},summary=result.summary(),frames=[dict(time=t,visible=v,serving=serving,delay=delay,snr=snr,satellites=[dict(id=s.satellite_id,xyz=[x/1000 for x in s.position_ecef_m],altitude=(sum(x*x for x in s.position_ecef_m)**.5-EARTH_RADIUS_M)/1000,speed=sum(x*x for x in s.velocity_teme_m_s)**.5/1000) for s in states]) for t,v,serving,delay,snr,states in zip(result.times_seconds,result.visible_counts,result.serving_satellite_ids,result.serving_delays_ms,result.serving_snr_db,result.satellite_states)],events=[dict(time=e.time_seconds,previous=e.previous_satellite_id,next=e.next_satellite_id,reason=e.reason) for e in result.handovers])

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT/'frontend'),**kwargs)
    def do_GET(self):
        url=urlparse(self.path)
        if url.path=='/health':
            self.send_response(200);self.end_headers();self.wfile.write(b'ok');return
        if url.path=='/earth.jpg':
            body=(ROOT/'src/orbitlink/dashboard/assets/earth.jpg').read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.end_headers();self.wfile.write(body);return
        if url.path=='/api/scenario':
            try:
                q=parse_qs(url.query);group=q.get('group',['Iridium NEXT'])[0]
                if group not in ('Starlink','Iridium NEXT'):raise ValueError('Unknown catalog')
                count=int(q.get('count',['150'])[0]);lat=float(q.get('lat',['37.7749'])[0]);lon=float(q.get('lon',['-122.4194'])[0])
                if count != 0 and not 10<=count<=500:raise ValueError('Count must be 0 (full catalog) or 10–500')
                GroundSite('Terminal',lat,lon)
                payload=scenario(group,count,lat,lon,int(datetime.now(timezone.utc).timestamp()//60));status=200
            except Exception as exc:payload={'error':str(exc)};status=400
            body=json.dumps(payload).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body);return
        super().do_GET()

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8000'))),Handler).serve_forever()

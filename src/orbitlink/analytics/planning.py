"""Obstruction-mask site comparison over sampled orbital positions."""
import math
from orbitlink.core.models import GroundSite
from orbitlink.geometry.transforms import look_angle

def compare_sites(frames, sites, minimum_elevation=25):
    if not frames or not 1 <= len(sites) <= 3:raise ValueError('Provide 1–3 sites and nonempty orbital samples')
    names=[str(item.get('name','')).strip() for item in sites]
    if any(not name for name in names) or len(set(names))!=len(names):raise ValueError('Each placement needs a unique nonempty name')
    results=[]
    for item in sites:
        site=GroundSite(str(item['name'])[:60],float(item['lat']),float(item['lon']))
        mask=[float(v) for v in item['mask']]
        if len(mask)!=8 or any(not math.isfinite(v) or not 0<=v<=90 for v in mask):raise ValueError('Each site needs eight obstruction elevations between 0 and 90 degrees')
        counts=[]
        for frame in frames:
            count=0
            for sat in frame['satellites']:
                angle=look_angle(site,sat['id'],tuple(v*1000 for v in sat['xyz']),minimum_elevation)
                sector=int((angle.azimuth_deg+22.5)%360//45)
                if angle.visible and angle.elevation_deg>=mask[sector]:count+=1
            counts.append(count)
        gaps=[];start=None
        for i,n in enumerate(counts):
            if n==0 and start is None:start=frames[i]['time']
            if n>0 and start is not None:gaps.append({'start_s':start,'end_s':frames[i]['time']});start=None
        if start is not None:gaps.append({'start_s':start,'end_s':frames[-1]['time']})
        results.append(dict(name=site.name,lat=site.latitude_deg,lon=site.longitude_deg,mask=mask,counts=counts,sampled_visibility_percent=100*sum(n>0 for n in counts)/len(counts),mean_visible=sum(counts)/len(counts),longest_sampled_gap_s=max((g['end_s']-g['start_s'] for g in gaps),default=0),gaps=gaps))
    results.sort(key=lambda r:(-r['sampled_visibility_percent'],r['longest_sampled_gap_s'],-r['mean_visible']))
    best=results[0]
    ties=[r['name'] for r in results if (r['sampled_visibility_percent'],r['longest_sampled_gap_s'],r['mean_visible'])==(best['sampled_visibility_percent'],best['longest_sampled_gap_s'],best['mean_visible'])]
    return dict(tied_sites=ties,sites=results,recommended='Tie: '+', '.join(ties) if len(ties)>1 else best['name'],assumptions='Eight 45-degree sky sectors: N, NE, E, SE, S, SW, W, NW. Mask values are user-supplied obstacle elevations. Ranking uses sampled visibility, gap length, then mean satellite count; it is not a prediction of operator service or throughput. Gaps are quantized to the sample interval.')

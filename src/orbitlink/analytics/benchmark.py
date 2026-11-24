"""Seeded, discrete-time comparison under identical link conditions."""
import hashlib

def benchmark(seed=42, loss_percent=10, outage_start=10, outage_end=25):
    seed=int(seed);loss=float(loss_percent);start=int(outage_start);end=int(outage_end)
    if not 0<=loss<=100 or not 0<=start<end<=60:raise ValueError('Loss 0–100%, outage 0–60 seconds required')
    generated=list(range(0,60,3));results=[]
    def succeeds(message,t):
        if start<=t<end:return False
        draw=int.from_bytes(hashlib.sha256(f'{seed}:{message}:{t}'.encode()).digest()[:8],'big')/2**64
        return draw>=loss/100
    for strategy in ('Direct only','Limited retry (9 seconds)','Persistent queue'):
        delays=[];pending=0;dropped=0;attempts=0;timeline=[]
        for identity,created in enumerate(generated):
            deadline=created if strategy=='Direct only' else min(89,created+9) if strategy.startswith('Limited') else 89
            delivered=None
            for t in range(created,deadline+1,3):
                attempts+=1
                if succeeds(identity,t):delivered=t;break
            if delivered is not None:delays.append(delivered-created)
            elif strategy=='Persistent queue':pending+=1
            else:dropped+=1
            timeline.append(dict(message=identity,created_s=created,delivered_s=delivered))
        results.append(dict(strategy=strategy,generated=len(generated),delivered=len(delays),delivery_percent=100*len(delays)/len(generated),pending=pending,dropped=dropped,attempts=attempts,mean_delay_s=sum(delays)/len(delays) if delays else None,max_delay_s=max(delays) if delays else None,timeline=timeline))
    return dict(seed=seed,loss_percent=loss,outage_start_s=start,outage_end_s=end,observation_end_s=89,results=results,assumptions='Discrete-time simulation: 20 messages generated every 3 seconds; retry interval 3 seconds; outage plus independent seeded loss per message/time attempt; shared link trace across strategies. Delays are simulated queue delays, not measured network latency. Persistent messages remain pending at the observation horizon. No process restart is simulated.')

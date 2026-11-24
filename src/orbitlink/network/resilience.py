"""Persistent store-and-forward demonstration over a controlled local link."""
import sqlite3
import os
import json
from urllib.request import Request,urlopen
import time
import uuid
import threading
import random
import math
from pathlib import Path

class ResilienceDemo:
    def __init__(self, path):
        self.path=str(path);self.lock=threading.RLock();self.online=True
        self.last_delivery_error=None
        self.delay_ms=0;self.jitter_ms=0;self.loss_percent=0
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)')
            row=db.execute("SELECT value FROM settings WHERE key='online'").fetchone()
            if row is not None:self.online=bool(row[0])
            db.execute('CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, body TEXT, created REAL, delivered REAL, direct_delivered INTEGER)')
    def connect(self):
        return sqlite3.connect(self.path,timeout=10)
    def configure(self, delay_ms=0, jitter_ms=0, loss_percent=0):
        values=[float(delay_ms),float(jitter_ms),float(loss_percent)]
        if any(not math.isfinite(x) for x in values) or not 0<=values[0]<=2000 or not 0<=values[1]<=1000 or not 0<=values[2]<=100:
            raise ValueError('Delay 0–2000 ms, jitter 0–1000 ms, loss 0–100% required')
        with self.lock:
            self.delay_ms,self.jitter_ms,self.loss_percent=values
        return self.status()
    def deliver(self, identity, body):
        # Independent Bernoulli loss per attempt; jitter is uniform, clipped at zero.
        if random.random()*100 < self.loss_percent:
            self.last_delivery_error='Emulated packet loss';return False
        delay=max(0,self.delay_ms+random.uniform(-self.jitter_ms,self.jitter_ms))
        if delay:time.sleep(delay/1000)

        url=os.environ.get('ORBITLINK_RECEIVER_URL')
        if not url:
            self.last_delivery_error=None;return True
        try:
            request=Request(url.rstrip('/')+'/messages',data=json.dumps({'id':identity,'body':body}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ.get('ORBITLINK_RECEIVER_TOKEN','')},method='POST')
            with urlopen(request,timeout=3) as response:
                ack=json.load(response)
            delivered=ack.get('ack')==identity
            self.last_delivery_error=None if delivered else 'Receiver acknowledgement did not match message ID'
            return delivered
        except (OSError,ValueError) as exc:
            self.last_delivery_error='Receiver unreachable or rejected delivery: '+str(exc);return False
    def send(self, body):
        if not isinstance(body,str) or not body.strip() or len(body)>500:
            raise ValueError('Message must contain 1–500 characters')
        with self.lock,self.connect() as db:
            now=time.time();identity=str(uuid.uuid4());delivered=self.online and self.deliver(identity,body.strip())
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?)',(identity,body.strip(),now,time.time() if delivered else None,int(delivered)))
        return self.status()
    def link(self, online):
        if not isinstance(online,bool):raise ValueError('online must be boolean')
        with self.lock,self.connect() as db:
            self.online=online
            db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",('online',int(online)))
            if online:
                for identity,body in db.execute('SELECT id,body FROM messages WHERE delivered IS NULL ORDER BY created LIMIT 5').fetchall():
                    if self.deliver(identity,body):db.execute('UPDATE messages SET delivered=? WHERE id=?',(time.time(),identity))
        return self.status()
    def status(self):
        with self.lock,self.connect() as db:
            rows=db.execute('SELECT id,body,created,delivered,direct_delivered FROM messages ORDER BY created').fetchall()
        messages=[dict(id=r[0],body=r[1],created=r[2],delivered=r[3],direct_delivered=bool(r[4]),delay_seconds=None if r[3] is None else r[3]-r[2]) for r in rows]
        return dict(last_delivery_error=self.last_delivery_error,retry_interval_seconds=10,emulation=dict(delay_ms=self.delay_ms,jitter_ms=self.jitter_ms,loss_percent=self.loss_percent),online=self.online,generated=len(rows),queued=sum(r[3] is None for r in rows),delivered=sum(r[3] is not None for r in rows),direct_delivered=sum(r[4] for r in rows),messages=messages,mode='Acknowledged HTTP receiver' if os.environ.get('ORBITLINK_RECEIVER_URL') else 'Controlled local delivery demonstration')

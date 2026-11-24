"""Persistent store-and-forward demonstration over a controlled local link."""
import sqlite3
import os
import json
from urllib.request import Request,urlopen
import time
import uuid
import threading
from pathlib import Path

class ResilienceDemo:
    def __init__(self, path):
        self.path=str(path);self.lock=threading.RLock();self.online=True
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)')
            row=db.execute("SELECT value FROM settings WHERE key='online'").fetchone()
            if row is not None:self.online=bool(row[0])
            db.execute('CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, body TEXT, created REAL, delivered REAL, direct_delivered INTEGER)')
    def connect(self):
        return sqlite3.connect(self.path,timeout=10)
    def deliver(self, identity, body):
        url=os.environ.get('ORBITLINK_RECEIVER_URL')
        if not url:return True
        try:
            request=Request(url.rstrip('/')+'/messages',data=json.dumps({'id':identity,'body':body}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ.get('ORBITLINK_RECEIVER_TOKEN','')},method='POST')
            with urlopen(request,timeout=3) as response:
                ack=json.load(response)
            return ack.get('ack')==identity
        except (OSError,ValueError):return False
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
                for identity,body in db.execute('SELECT id,body FROM messages WHERE delivered IS NULL').fetchall():
                    if self.deliver(identity,body):db.execute('UPDATE messages SET delivered=? WHERE id=?',(time.time(),identity))
        return self.status()
    def status(self):
        with self.lock,self.connect() as db:
            rows=db.execute('SELECT id,body,created,delivered,direct_delivered FROM messages ORDER BY created').fetchall()
        messages=[dict(id=r[0],body=r[1],created=r[2],delivered=r[3],direct_delivered=bool(r[4]),delay_seconds=None if r[3] is None else r[3]-r[2]) for r in rows]
        return dict(online=self.online,generated=len(rows),queued=sum(r[3] is None for r in rows),delivered=sum(r[3] is not None for r in rows),direct_delivered=sum(r[4] for r in rows),messages=messages,mode='Acknowledged HTTP receiver' if os.environ.get('ORBITLINK_RECEIVER_URL') else 'Controlled local delivery demonstration')

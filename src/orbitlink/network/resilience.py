"""Persistent store-and-forward demonstration over a controlled local link."""
import sqlite3
import time
import uuid
import threading
from pathlib import Path

class ResilienceDemo:
    def __init__(self, path):
        self.path=str(path);self.lock=threading.RLock();self.online=True
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, body TEXT, created REAL, delivered REAL, direct_delivered INTEGER)')
    def connect(self):
        return sqlite3.connect(self.path,timeout=10)
    def send(self, body):
        if not isinstance(body,str) or not body.strip() or len(body)>500:
            raise ValueError('Message must contain 1–500 characters')
        with self.lock,self.connect() as db:
            now=time.time();db.execute('INSERT INTO messages VALUES (?,?,?,?,?)',(str(uuid.uuid4()),body.strip(),now,now if self.online else None,int(self.online)))
        return self.status()
    def link(self, online):
        if not isinstance(online,bool):raise ValueError('online must be boolean')
        with self.lock,self.connect() as db:
            self.online=online
            if online:db.execute('UPDATE messages SET delivered=? WHERE delivered IS NULL',(time.time(),))
        return self.status()
    def status(self):
        with self.lock,self.connect() as db:
            rows=db.execute('SELECT id,body,created,delivered,direct_delivered FROM messages ORDER BY created').fetchall()
        messages=[dict(id=r[0],body=r[1],created=r[2],delivered=r[3],direct_delivered=bool(r[4]),delay_seconds=None if r[3] is None else r[3]-r[2]) for r in rows]
        return dict(online=self.online,generated=len(rows),queued=sum(r[3] is None for r in rows),delivered=sum(r[3] is not None for r in rows),direct_delivered=sum(r[4] for r in rows),messages=messages,mode='Controlled link emulation; application messages are stored and delivered locally, not through a satellite')

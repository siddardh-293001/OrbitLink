"""Server-only PostgreSQL stores; private schemas and separate runtime roles."""
from contextlib import contextmanager
import threading
import time
import uuid
from orbitlink.network.resilience import ResilienceDemo

class StorageUnavailable(RuntimeError):
    """Safe public error; never return connection credentials to API clients."""

@contextmanager
def connection(dsn):
    import psycopg
    # Transaction pooling is compatible with these short, explicitly closed connections.
    try:
        with psycopg.connect(dsn, connect_timeout=8, prepare_threshold=None,
                             options='-c statement_timeout=10000') as db:
            yield db
    except psycopg.OperationalError as exc:
        raise StorageUnavailable('Message storage is temporarily unavailable. Please retry shortly.') from exc

class PostgresDemo(ResilienceDemo):
    def __init__(self, session, dsn):
        self.session=str(uuid.UUID(session)); self.dsn=dsn
        self.lock=threading.RLock(); self.last_delivery_error=None
        self.delay_ms=0; self.jitter_ms=0; self.loss_percent=0
        with connection(dsn) as db:
            db.execute('INSERT INTO orbitlink_sender.sessions(id) VALUES (%s) ON CONFLICT DO NOTHING',(self.session,))
            self.read_settings(db)

    def read_settings(self, db, lock=False):
        row=db.execute('SELECT online,delay_ms,jitter_ms,loss_percent FROM orbitlink_sender.sessions WHERE id=%s'+(' FOR UPDATE' if lock else ''),(self.session,)).fetchone()
        self.online,self.delay_ms,self.jitter_ms,self.loss_percent=row

    def configure(self, delay_ms=0, jitter_ms=0, loss_percent=0):
        # Validate ranges and preserve configured conditions for recovery workers.
        import math
        values=[float(delay_ms),float(jitter_ms),float(loss_percent)]
        if any(not math.isfinite(v) for v in values) or not 0<=values[0]<=2000 or not 0<=values[1]<=1000 or not 0<=values[2]<=100:
            raise ValueError('Delay 0–2000 ms, jitter 0–1000 ms, loss 0–100% required')
        with self.lock,connection(self.dsn) as db:
            db.execute('UPDATE orbitlink_sender.sessions SET delay_ms=%s,jitter_ms=%s,loss_percent=%s WHERE id=%s',(*values,self.session))
        return self.status()

    def attempt(self, db, identity, body):
        started=time.time(); acknowledged=self.deliver(identity,body)
        db.execute('INSERT INTO orbitlink_sender.attempts(message_id,attempted_at,acknowledged,detail) VALUES (%s,to_timestamp(%s),%s,%s)',
                   (identity,started,acknowledged,'Acknowledged' if acknowledged else self.last_delivery_error or 'Not acknowledged'))
        return acknowledged

    def send(self, body):
        if not isinstance(body,str) or not body.strip() or len(body)>500:
            raise ValueError('Message must contain 1–500 characters')
        identity=str(uuid.uuid4()); body=body.strip()
        # Commit the queue before network I/O: a crash cannot lose an accepted message.
        with self.lock:
            with connection(self.dsn) as db:
                self.read_settings(db,lock=True)
                db.execute('INSERT INTO orbitlink_sender.messages(id,session_id,body) VALUES (%s,%s,%s)',(identity,self.session,body))
            if self.online:
                with connection(self.dsn) as db:
                    self.read_settings(db,lock=True)
                    pending=db.execute('SELECT delivered_at FROM orbitlink_sender.messages WHERE id=%s',(identity,)).fetchone()[0] is None
                    if self.online and pending and self.attempt(db,identity,body):
                        db.execute('UPDATE orbitlink_sender.messages SET delivered_at=clock_timestamp(),direct_delivered=true WHERE id=%s AND session_id=%s',(identity,self.session))
        return self.status()

    def link(self, online):
        if not isinstance(online,bool):raise ValueError('online must be boolean')
        return self._link(online)

    def retry(self):
        return self._link(None)

    def _link(self, online):
        with self.lock,connection(self.dsn) as db:
            # Session row serializes deliveries across processes as well as threads.
            self.read_settings(db,lock=True)
            if online is not None:
                db.execute('UPDATE orbitlink_sender.sessions SET online=%s WHERE id=%s',(online,self.session))
                self.online=online
            if self.online:
                rows=db.execute('SELECT id,body FROM orbitlink_sender.messages WHERE session_id=%s AND delivered_at IS NULL ORDER BY created_at LIMIT 5',(self.session,)).fetchall()
                for identity,body in rows:
                    if self.attempt(db,str(identity),body):
                        db.execute('UPDATE orbitlink_sender.messages SET delivered_at=clock_timestamp() WHERE id=%s AND session_id=%s',(identity,self.session))
        return self.status()

    def status(self):
        with self.lock,connection(self.dsn) as db:
            self.read_settings(db)
            rows=db.execute('SELECT id,body,extract(epoch from created_at)::float8,extract(epoch from delivered_at)::float8,direct_delivered FROM orbitlink_sender.messages WHERE session_id=%s ORDER BY created_at',(self.session,)).fetchall()
            attempts=db.execute('SELECT a.message_id,extract(epoch from a.attempted_at)::float8,a.acknowledged,a.detail FROM orbitlink_sender.attempts a JOIN orbitlink_sender.messages m ON m.id=a.message_id WHERE m.session_id=%s ORDER BY a.attempted_at',(self.session,)).fetchall()
        rows=[(str(r[0]),*r[1:]) for r in rows]
        attempts=[(str(a[0]),*a[1:]) for a in attempts]
        return self.format_status(rows,attempts,storage='PostgreSQL (hosted durable storage)')

    @classmethod
    def pending_sessions(cls, dsn):
        with connection(dsn) as db:
            return [str(r[0]) for r in db.execute('SELECT DISTINCT s.id FROM orbitlink_sender.sessions s JOIN orbitlink_sender.messages m ON m.session_id=s.id WHERE s.online AND m.delivered_at IS NULL LIMIT 100').fetchall()]

class PostgresReceiver:
    def __init__(self, dsn):self.dsn=dsn
    def accept(self, identity, body):
        if not isinstance(identity,str) or not 1<=len(identity)<=80 or not isinstance(body,str) or not 1<=len(body)<=500:
            raise ValueError('Invalid message')
        with connection(self.dsn) as db:
            inserted=db.execute('INSERT INTO orbitlink_receiver.receipts(message_id,body) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING message_id',(identity,body)).fetchone()
            previous=db.execute('SELECT body FROM orbitlink_receiver.receipts WHERE message_id=%s',(identity,)).fetchone()
            if previous[0]!=body:raise ValueError('Message ID conflicts with existing content')
        return dict(ack=identity,duplicate=inserted is None)

"""Independent acknowledged message receiver. Run with python -m orbitlink.network.receiver."""
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class ReceiverStore:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:db.execute('CREATE TABLE IF NOT EXISTS received (id TEXT PRIMARY KEY, body TEXT)')
    def accept(self,identity,body):
        if not isinstance(identity,str) or not 1<=len(identity)<=80 or not isinstance(body,str) or not 1<=len(body)<=500:raise ValueError('Invalid message')
        with sqlite3.connect(self.path) as db:
            previous=db.execute('SELECT body FROM received WHERE id=?',(identity,)).fetchone()
            if previous and previous[0]!=body:raise ValueError('Message ID conflicts with existing content')
            db.execute('INSERT OR IGNORE INTO received VALUES (?,?)',(identity,body))
        return dict(ack=identity,duplicate=previous is not None)

class ReceiverHandler(BaseHTTPRequestHandler):
    store=None
    def do_GET(self):
        self.send_response(200 if self.path=='/health' else 404);self.end_headers();self.wfile.write(b'ok')
    def do_POST(self):
        try:
            import hmac
            token=os.environ.get('ORBITLINK_RECEIVER_TOKEN','')
            if not token or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                self.send_response(401);self.end_headers();return
            size=int(self.headers.get('Content-Length','0'))
            if self.path!='/messages' or not 0<size<=2048:raise ValueError('Invalid request')
            data=json.loads(self.rfile.read(size));result=self.store.accept(data['id'],data['body']);code=200
        except (ValueError,KeyError,TypeError) as exc:result={'error':str(exc)};code=400
        self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(result).encode())

if __name__=='__main__':
    directory=Path(os.environ.get('ORBITLINK_DATA_DIR',tempfile.gettempdir()));directory.mkdir(parents=True,exist_ok=True)
    ReceiverHandler.store=ReceiverStore(directory/'received.sqlite')
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8001'))),ReceiverHandler).serve_forever()

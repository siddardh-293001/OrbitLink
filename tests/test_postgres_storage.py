"""Opt-in hosted integration tests: set both ORBITLINK_TEST_*_DSN variables."""
import os
import unittest
import uuid
from unittest.mock import patch
from orbitlink.network.postgres import PostgresDemo, PostgresReceiver, connection

SENDER=os.environ.get('ORBITLINK_TEST_SENDER_DSN')
RECEIVER=os.environ.get('ORBITLINK_TEST_RECEIVER_DSN')

@unittest.skipUnless(SENDER and RECEIVER,'Hosted test database credentials not configured')
class HostedStorageTests(unittest.TestCase):
    def test_restart_queue_session_isolation_and_recovery(self):
        session=str(uuid.uuid4()); demo=PostgresDemo(session,SENDER)
        demo.link(False); state=demo.send('Durable integration test')
        identity=state['messages'][0]['id']
        demo.configure(10,5,0)
        restarted=PostgresDemo(session,SENDER)
        self.assertEqual(restarted.status()['emulation']['delay_ms'],10)
        self.assertFalse(restarted.online)
        self.assertEqual(restarted.status()['queued'],1)
        self.assertEqual(PostgresDemo(str(uuid.uuid4()),SENDER).status()['generated'],0)
        self.assertNotIn(session,PostgresDemo.pending_sessions(SENDER))
        with patch.object(restarted,'deliver',return_value=False):state=restarted.link(True)
        self.assertEqual(state['queued'],1)
        self.assertIn(session,PostgresDemo.pending_sessions(SENDER))
        receiver=PostgresReceiver(RECEIVER)
        with patch.object(restarted,'deliver',side_effect=lambda i,b:receiver.accept(i,b)['ack']==i):
            state=restarted.link(True)
        self.assertEqual(state['delivered'],1)
        self.assertEqual(state['messages'][0]['id'],identity)
        self.assertEqual(state['messages'][0]['attempt_count'],2)
        self.assertEqual(PostgresDemo(session,SENDER).status()['delivered'],1)
        self.assertTrue(PostgresReceiver(RECEIVER).accept(identity,'Durable integration test')['duplicate'])
        with self.assertRaises(ValueError):receiver.accept(identity,'Conflicting content')

    def test_separate_runtime_role_privileges(self):
        import psycopg
        for dsn,table in [(SENDER,'orbitlink_receiver.receipts'),(RECEIVER,'orbitlink_sender.messages')]:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with connection(dsn) as db:db.execute('SELECT * FROM '+table)

    def test_queue_survives_delivery_exception(self):
        session=str(uuid.uuid4());demo=PostgresDemo(session,SENDER)
        with patch.object(demo,'deliver',side_effect=RuntimeError('Process interrupted')):
            with self.assertRaises(RuntimeError):demo.send('Accepted before delivery')
        self.assertEqual(PostgresDemo(session,SENDER).status()['queued'],1)

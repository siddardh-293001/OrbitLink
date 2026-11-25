BEGIN;
CREATE SCHEMA IF NOT EXISTS orbitlink_sender;
CREATE SCHEMA IF NOT EXISTS orbitlink_receiver;
CREATE TABLE IF NOT EXISTS orbitlink_sender.sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    online BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS orbitlink_sender.messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES orbitlink_sender.sessions(id),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    direct_delivered BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS pending_by_session ON orbitlink_sender.messages(session_id, created_at) WHERE delivered_at IS NULL;
CREATE TABLE IF NOT EXISTS orbitlink_sender.attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES orbitlink_sender.messages(id),
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged BOOLEAN NOT NULL,
    detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orbitlink_receiver.receipts (
    message_id TEXT PRIMARY KEY CHECK (length(message_id) BETWEEN 1 AND 80),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 500),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
REVOKE ALL ON SCHEMA orbitlink_sender, orbitlink_receiver FROM PUBLIC, anon, authenticated;
CREATE ROLE orbitlink_sender_runtime LOGIN;
CREATE ROLE orbitlink_receiver_runtime LOGIN;
GRANT USAGE ON SCHEMA orbitlink_sender TO orbitlink_sender_runtime;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA orbitlink_sender TO orbitlink_sender_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA orbitlink_sender TO orbitlink_sender_runtime;
GRANT USAGE ON SCHEMA orbitlink_receiver TO orbitlink_receiver_runtime;
GRANT SELECT,INSERT ON orbitlink_receiver.receipts TO orbitlink_receiver_runtime;
ALTER TABLE orbitlink_sender.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE orbitlink_sender.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE orbitlink_sender.attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE orbitlink_receiver.receipts ENABLE ROW LEVEL SECURITY;
CREATE POLICY backend_access ON orbitlink_sender.sessions TO orbitlink_sender_runtime USING (true) WITH CHECK (true);
CREATE POLICY backend_access ON orbitlink_sender.messages TO orbitlink_sender_runtime USING (true) WITH CHECK (true);
CREATE POLICY backend_access ON orbitlink_sender.attempts TO orbitlink_sender_runtime USING (true) WITH CHECK (true);
CREATE POLICY backend_access ON orbitlink_receiver.receipts TO orbitlink_receiver_runtime USING (true) WITH CHECK (true);
COMMIT;


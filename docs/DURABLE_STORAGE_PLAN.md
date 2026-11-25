# Durable delivery storage

ORBITLINK supports external PostgreSQL through ORBITLINK_DATABASE_URL on each service. The sender and receiver use separate runtime roles and private schemas. Credentials are configured only in Render environment variables, never in frontend assets or migrations. Supabase RLS is enabled; anon and authenticated roles have no schema access. Browser session IDs remain bearer capabilities, not authenticated user accounts.

Sender storage includes queue contents, stable IDs, delivery times, direct-only baseline outcomes, attempt evidence, online state and emulated link conditions. A message is committed before outbound HTTP delivery. Receiver acknowledgements are issued only after its receipt transaction commits. Repeating the same ID and content is idempotent; conflicting content is rejected. This provides at-least-once attempts with duplicate suppression, not a claim of exactly-once network delivery.

The retry worker discovers pending online sessions from PostgreSQL after application restart, even without a browser reconnect. Database errors return a generic 503; they never silently switch to ephemeral storage. Without ORBITLINK_DATABASE_URL, local development retains SQLite mode.

## Free provider limits

Provider: Supabase Free, Singapore, project ORBITLINK. Published free quotas include 500 MB database storage, 5 GB egress and two active projects. Free projects pause after one week of inactivity. This is suitable for the expo, not a guaranteed always-on production service. Retain exported reports; automated backups and production SLA are not promised by this implementation. No paid resources or paid add-ons were requested.

Reference: https://supabase.com/pricing

## Deployment and verification

The numbered SQL files in migrations record the applied hosted migrations. Runtime roles are provisioned separately with generated passwords; migration SQL contains no credentials. The Supabase CLI migration command was attempted but its binary exited with SIGKILL; files use the migration versions returned by the hosted migration history.

Local tests: 48 existing checks plus 3 opt-in hosted integration checks covering restart recovery, persisted link conditions, session separation, failed acknowledgement recovery, duplicate receipts, interrupted sends and runtime role restrictions. Run hosted tests with ORBITLINK_TEST_SENDER_DSN and ORBITLINK_TEST_RECEIVER_DSN; do not commit these values.

A deployed acceptance check must create an offline queued message, redeploy both services, confirm the same ID remains pending, restore the link, verify receipt and attempt evidence, then redeploy and verify acknowledgement history again. Record its outcome in release evidence.

Previous ephemeral SQLite demonstration data is not automatically imported. No claim is made that records lost in earlier Render redeploys can be recovered. Browser-local planning surveys remain separate and device-local.

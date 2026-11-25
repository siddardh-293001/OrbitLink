ALTER TABLE orbitlink_sender.sessions
  ADD COLUMN delay_ms double precision NOT NULL DEFAULT 0 CHECK (delay_ms BETWEEN 0 AND 2000),
  ADD COLUMN jitter_ms double precision NOT NULL DEFAULT 0 CHECK (jitter_ms BETWEEN 0 AND 1000),
  ADD COLUMN loss_percent double precision NOT NULL DEFAULT 0 CHECK (loss_percent BETWEEN 0 AND 100);

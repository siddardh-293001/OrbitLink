# Independent acknowledged receiver

Run `python -m orbitlink.network.receiver` in a separate process or service. It listens on PORT (default 8001). Set ORBITLINK_RECEIVER_TOKEN to a secret shared by the sender and receiver. The receiver refuses unauthenticated message submissions. Set ORBITLINK_DATA_DIR to persistent storage for receiver records.

On Mission Control, set ORBITLINK_RECEIVER_URL to that receiver's base URL and ORBITLINK_RECEIVER_TOKEN to the same secret. Do not commit secrets. The sender marks delivery only after an acknowledgement with the matching message ID. Failed or missing acknowledgement leaves the message queued; Restore connection retries queued messages. Repeated retries are idempotent at the receiver. Automatic periodic retry, external durable database storage and operational monitoring are still pending.

Without ORBITLINK_RECEIVER_URL, the existing controlled local-delivery mode remains active. This preserves the current exhibit while a receiver is provisioned. Deployment has not yet been connected to a separate hosted receiver. Neither mode transmits via a satellite.

Tests: `PYTHONPATH=src python -m unittest discover -s tests -p test_receiver.py -v`.

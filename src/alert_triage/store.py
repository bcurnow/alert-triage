import json
import sqlite3
import threading

from alert_triage.models import Alert

SCHEMA = """
CREATE TABLE IF NOT EXISTS pending (fingerprint TEXT PRIMARY KEY, alert TEXT NOT NULL, arrived REAL NOT NULL);
CREATE TABLE IF NOT EXISTS cooldown (fingerprint TEXT PRIMARY KEY, last_dispatched REAL NOT NULL);
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY, opened REAL NOT NULL, dispatched REAL NOT NULL, outcome TEXT NOT NULL,
    alert_count INTEGER NOT NULL, kept_count INTEGER NOT NULL, suppressed_count INTEGER NOT NULL, detail TEXT NOT NULL
);
"""


class Store:
    """Pending alerts survive a restart; cooldown and incident history persist for grading."""

    def __init__(self, path):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    def add_pending(self, alert, arrived):
        with self._lock, self._db:
            self._db.execute('INSERT OR REPLACE INTO pending VALUES (?, ?, ?)', (alert.fingerprint, alert.to_json(), arrived))

    def remove_pending(self, fingerprint):
        with self._lock, self._db:
            self._db.execute('DELETE FROM pending WHERE fingerprint = ?', (fingerprint,))

    def load_pending(self):
        with self._lock:
            rows = self._db.execute('SELECT alert, arrived FROM pending ORDER BY arrived').fetchall()
        return [(Alert.from_json(a), arrived) for a, arrived in rows]

    def in_cooldown(self, fingerprint, now, window):
        with self._lock:
            row = self._db.execute('SELECT last_dispatched FROM cooldown WHERE fingerprint = ?', (fingerprint,)).fetchone()
        return row is not None and now - row[0] < window

    def mark_dispatched(self, alerts, now):
        with self._lock, self._db:
            self._db.executemany('INSERT OR REPLACE INTO cooldown VALUES (?, ?)', [(a.fingerprint, now) for a in alerts])

    def record_incident(self, incident, dispatched, outcome, kept, suppressed, detail):
        with self._lock, self._db:
            self._db.execute(
                'INSERT OR REPLACE INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (incident.id, incident.opened_at, dispatched, outcome, len(incident.alerts), len(kept), len(suppressed), json.dumps(detail)),
            )

    def incidents(self):
        with self._lock:
            return self._db.execute('SELECT id, opened, dispatched, outcome, alert_count, kept_count, suppressed_count, detail FROM incidents ORDER BY opened').fetchall()

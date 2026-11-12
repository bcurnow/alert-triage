import sqlite3

from alert_triage.store import Store


def test_an_existing_cooldown_table_is_migrated_in_place(tmp_path):
    path = str(tmp_path / 'state.db')
    old = sqlite3.connect(path)
    old.execute('CREATE TABLE cooldown (fingerprint TEXT PRIMARY KEY, last_dispatched REAL NOT NULL)')
    old.execute("INSERT INTO cooldown VALUES ('abc', 100)")
    old.commit()
    old.close()
    store = Store(path)
    assert store.in_cooldown('abc', 150, 100)
    assert not store.in_cooldown('abc', 250, 100)
    Store(path)

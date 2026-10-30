from alert_triage.config import Config


def test_cooldown_defaults_to_one_day():
    assert Config(mail_to='me@example.com').cooldown_seconds == 86400

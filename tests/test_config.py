from alert_triage.config import Config


def test_cooldown_defaults_to_one_day():
    assert Config(mail_to='me@example.com').cooldown_seconds == 86400


def test_debounce_defaults_wide_enough_for_alerts_whose_for_durations_differ():
    assert Config(mail_to='me@example.com').debounce_seconds == 900

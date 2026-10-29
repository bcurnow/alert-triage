from alert_triage.store import Store
from conftest import make_alert


def test_filters_severity_and_ignored_names(build):
    service, _, _, _ = build()
    service.ingest([make_alert(severity='info'), make_alert(name='Watchdog', severity='none'), make_alert()], now=0)
    assert service.pending() == 1


def test_emails_once_per_incident_with_still_firing_alerts(build):
    a, b = make_alert(target='a'), make_alert(target='b')
    service, _, mailer, store = build(active={a.fingerprint})
    service.ingest([a, b], now=0)
    assert service.tick(now=100) is None
    service.tick(now=300)
    assert len(mailer.sent) == 1
    subject, body = mailer.sent[0]
    assert subject.startswith('[triage] 1 alert: HostDown')
    assert 'No longer active at dispatch (1): HostDown x1' in body
    assert store.incidents()[0][3] == 'emailed'


def test_all_resolved_is_recorded_but_not_mailed(build):
    service, _, mailer, store = build(active=set())
    service.ingest([make_alert()], now=0)
    service.tick(now=300)
    assert mailer.sent == []
    assert store.incidents()[0][3] == 'self_resolved'


def test_cooldown_holds_back_a_repeat_then_expires(build):
    alert = make_alert()
    service, am, mailer, store = build(active={alert.fingerprint})
    service.ingest([alert], now=0)
    service.tick(now=300)
    service.ingest([alert], now=4 * 3600)
    assert service.pending() == 0
    service.ingest([alert], now=300 + 21600 + 1)
    assert service.pending() == 1


def test_suppressed_alerts_are_reported_in_the_next_digest(build):
    first, other = make_alert(target='a'), make_alert(target='b')
    service, am, mailer, store = build(active={first.fingerprint, other.fingerprint})
    service.ingest([first], now=0)
    service.tick(now=300)
    service.ingest([first, other], now=3600)
    service.tick(now=3600 + 300)
    assert 'Held back by the cooldown since the last digest (1): HostDown x1' in mailer.sent[1][1]


def test_alertmanager_failure_fails_open(build):
    service, _, mailer, store = build(fail_am=True)
    service.ingest([make_alert()], now=0)
    service.tick(now=300)
    assert len(mailer.sent) == 1
    assert 'could not be queried' in mailer.sent[0][1]


def test_mail_failure_is_recorded_and_does_not_start_cooldown(build):
    alert = make_alert()
    service, _, _, store = build(active={alert.fingerprint}, fail_mail=True)
    service.ingest([alert], now=0)
    service.tick(now=300)
    assert store.incidents()[0][3] == 'mail_failed'
    service.ingest([alert], now=400)
    assert service.pending() == 1


def test_pending_alerts_survive_a_restart(build, tmp_path):
    alert = make_alert()
    path = str(tmp_path / 'state.db')
    service, _, _, _ = build(store=Store(path))
    service.ingest([alert], now=0)
    restarted, _, mailer, _ = build(active={alert.fingerprint}, store=Store(path))
    restarted.restore()
    assert restarted.pending() == 1
    restarted.tick(now=300)
    assert len(mailer.sent) == 1

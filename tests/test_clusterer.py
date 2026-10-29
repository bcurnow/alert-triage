from alert_triage.clusterer import Clusterer
from conftest import make_alert


def test_quiet_period_releases_one_incident():
    c = Clusterer(debounce=300, max_hold=1800)
    for i in range(20):
        c.add(make_alert(target=f'h{i}'), now=i * 10)
    assert c.due(now=400) is None
    incident = c.due(now=190 + 300)
    assert len(incident.alerts) == 20
    assert c.due(now=10_000) is None


def test_repeat_notification_does_not_extend_quiet_timer():
    c = Clusterer(debounce=300, max_hold=1800)
    alert = make_alert()
    c.add(alert, now=0)
    assert c.add(alert, now=250) is False
    assert c.due(now=300) is not None


def test_continuous_storm_is_released_at_max_hold():
    c = Clusterer(debounce=300, max_hold=1800)
    for i in range(100):
        c.add(make_alert(target=f'h{i}'), now=i * 60)
    assert c.due(now=1799) is None
    assert len(c.due(now=1800).alerts) == 100


def test_next_arrival_after_release_starts_a_new_incident():
    c = Clusterer(debounce=300, max_hold=1800)
    c.add(make_alert(target='a'), now=0)
    first = c.due(now=300)
    c.add(make_alert(target='b'), now=400)
    second = c.due(now=700)
    assert first.id != second.id
    assert [a.target for a in second.alerts] == ['b']

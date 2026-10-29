from alert_triage.config import Config
from alert_triage.replay import Episode, simulate


def episode(name, target, start, end):
    return Episode({'alertname': name, 'severity': 'critical', 'instance': target}, start, end)


def test_a_storm_collapses_to_one_incident():
    storm = [episode('HostDown', f'h{i}', i * 20, i * 20 + 600) for i in range(40)]
    incidents, _ = simulate(storm, Config())
    assert len(incidents) == 1
    assert incidents[0][4] == 40


def test_blips_that_clear_before_dispatch_send_nothing():
    incidents, sent = simulate([episode('HostDown', 'a', 0, 120)], Config())
    assert [row[3] for row in incidents] == ['self_resolved']
    assert sent == 0


def test_a_lasting_alert_is_emailed_once_even_if_it_refires_in_cooldown():
    episodes = [episode('HostDown', 'a', 0, 4000), episode('HostDown', 'a', 6000, 9000)]
    incidents, sent = simulate(episodes, Config())
    assert sent == 1

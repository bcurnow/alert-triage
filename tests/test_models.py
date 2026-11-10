from alert_triage.models import fingerprint_of, parse_time, parse_webhook, target_of

PAYLOAD = {
    'version': '4',
    'alerts': [
        {
            'status': 'firing',
            'labels': {'alertname': 'HostDown', 'severity': 'critical', 'instance': 'ns1:9100'},
            'annotations': {'summary': 'down'},
            'startsAt': '2026-10-28T13:45:00.123456789Z',
            'fingerprint': 'abc',
        },
        {'status': 'resolved', 'labels': {'alertname': 'ProbeFailed'}, 'startsAt': '2026-10-28T13:00:00Z', 'fingerprint': 'def'},
    ],
}


def test_parse_webhook_splits_firing_and_resolved():
    firing, resolved = parse_webhook(PAYLOAD)
    assert [a.fingerprint for a in firing] == ['abc']
    assert resolved == ['def']
    assert firing[0].target == 'ns1:9100'
    assert firing[0].starts_at == 1793195100.123456


def test_parse_webhook_rejects_other_payloads():
    for bad in ([], {}, {'alerts': 'x'}):
        try:
            parse_webhook(bad)
        except ValueError:
            continue
        raise AssertionError(f'accepted {bad!r}')


def test_parse_time_handles_nanoseconds_and_plain_seconds():
    assert parse_time('2026-10-28T13:45:00Z') == parse_time('2026-10-28T13:45:00.999999999Z') - 0.999999


def test_target_names_the_workload_for_kubernetes_alerts_and_the_host_otherwise():
    assert target_of({'instance': 'h:1'}) == 'h:1'
    assert target_of({'instance': '10.97.6.169:8080', 'namespace': 'argocd', 'pod': 'argocd-dex-server-abc'}) == 'argocd/argocd-dex-server-abc'
    assert target_of({'namespace': 'iam', 'pod': 'keycloak-0'}) == 'iam/keycloak-0'
    assert target_of({'namespace': 'iam', 'statefulset': 'keycloak'}) == 'iam/keycloak'
    assert target_of({'namespace': 'monitoring'}) == 'monitoring'
    assert target_of({'job': 'probe'}) == 'probe'
    assert target_of({}) == ''


def test_target_prefers_the_argocd_app_over_the_exporter_pod():
    labels = {'instance': '10.97.3.130:8082', 'namespace': 'argocd', 'pod': 'argocd-application-controller-0', 'name': 'argocd'}
    assert target_of(labels) == 'argocd/argocd'


def test_fingerprint_is_stable_and_label_sensitive():
    assert fingerprint_of({'a': '1', 'b': '2'}) == fingerprint_of({'b': '2', 'a': '1'})
    assert fingerprint_of({'a': '1'}) != fingerprint_of({'a': '2'})

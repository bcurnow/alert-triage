import json
import threading
import urllib.error
import urllib.request

import pytest

from alert_triage.receiver import make_server


@pytest.fixture
def server(build):
    service, _, _, _ = build()
    httpd = make_server(service, '127.0.0.1', 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield service, f'http://127.0.0.1:{httpd.server_address[1]}'
    httpd.shutdown()


def post(url, body):
    request = urllib.request.Request(url, data=body, method='POST')
    return urllib.request.urlopen(request)


def test_webhook_feeds_the_service(server):
    service, base = server
    body = {'alerts': [{'status': 'firing', 'labels': {'alertname': 'HostDown', 'severity': 'critical', 'instance': 'a'}, 'startsAt': '2026-10-28T13:45:00Z'}]}
    assert post(f'{base}/webhook', json.dumps(body).encode()).status == 200
    assert json.load(urllib.request.urlopen(f'{base}/healthz')) == {'pending': 1}


@pytest.mark.parametrize('body', [b'not json', b'[]', b'{"alerts": 3}'])
def test_bad_payload_is_a_400(server, body):
    _, base = server
    with pytest.raises(urllib.error.HTTPError) as error:
        post(f'{base}/webhook', body)
    assert error.value.code == 400


def test_unknown_path_is_a_404(server):
    _, base = server
    with pytest.raises(urllib.error.HTTPError) as error:
        post(f'{base}/other', b'{}')
    assert error.value.code == 404


def test_a_resolved_notification_does_not_drop_a_pending_alert(server):
    service, base = server
    labels = {'alertname': 'HostDown', 'severity': 'critical', 'instance': 'a'}
    firing = {'alerts': [{'status': 'firing', 'labels': labels, 'startsAt': '2026-10-28T13:45:00Z', 'fingerprint': 'x'}]}
    resolved = {'alerts': [{'status': 'resolved', 'labels': labels, 'startsAt': '2026-10-28T13:45:00Z', 'fingerprint': 'x'}]}
    post(f'{base}/webhook', json.dumps(firing).encode())
    post(f'{base}/webhook', json.dumps(resolved).encode())
    assert service.pending() == 1

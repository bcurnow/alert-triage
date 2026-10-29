import pytest

from alert_triage.config import Config
from alert_triage.models import Alert
from alert_triage.service import Service
from alert_triage.store import Store


def make_alert(name='HostDown', target='ns1:9100', severity='critical', fingerprint=None, starts_at=1000.0):
    return Alert(fingerprint or f'{name}-{target}', name, severity, target, {'alertname': name, 'severity': severity, 'instance': target}, {'summary': f'{name} on {target}'}, starts_at)


class FakeAlertmanager:
    def __init__(self, active=None, fail=False):
        self.active = active
        self.fail = fail

    def active_fingerprints(self):
        if self.fail:
            raise OSError('unreachable')
        return self.active


class FakeMailer:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, subject, body):
        if self.fail:
            raise OSError('mail down')
        self.sent.append((subject, body))


@pytest.fixture
def config():
    return Config(mail_to='me@example.com', debounce_seconds=300, max_hold_seconds=1800, cooldown_seconds=21600)


@pytest.fixture
def build(config):
    def factory(active=None, fail_am=False, fail_mail=False, store=None):
        am = FakeAlertmanager(active=active if active is not None else set(), fail=fail_am)
        mailer = FakeMailer(fail=fail_mail)
        store = store or Store(':memory:')
        return Service(config, store, am, mailer), am, mailer, store

    return factory

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

_FRACTION = re.compile(r'(\.\d{6})\d+')


def parse_time(value):
    """RFC 3339 to epoch seconds; Alertmanager sends nanosecond fractions, which fromisoformat rejects."""
    return datetime.fromisoformat(_FRACTION.sub(r'\1', value).replace('Z', '+00:00')).timestamp()


def target_of(labels):
    """The thing a human would call the subject of the alert.

    Kubernetes alerts carry a namespace; their `instance` is only the exporter's scrape endpoint (kube-state-metrics,
    the Argo CD metrics port), so they are named by namespace and workload instead. `name` comes before `pod`
    because on Argo CD metrics `name` is the application and `pod` is the exporter. Everything else is the host
    (`instance`), then the job.
    """
    namespace = labels.get('namespace', '')
    if namespace:
        workload = next((labels[k] for k in ('name', 'deployment', 'statefulset', 'daemonset', 'job_name', 'pod') if labels.get(k)), '')
        return f'{namespace}/{workload}'.strip('/')
    return labels.get('instance') or labels.get('job', '')


def fingerprint_of(labels):
    return hashlib.sha1(json.dumps(sorted(labels.items())).encode()).hexdigest()[:16]


@dataclass
class Alert:
    fingerprint: str
    alertname: str
    severity: str
    target: str
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    starts_at: float = 0.0

    def to_json(self):
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, text):
        return cls(**json.loads(text))


def parse_webhook(payload):
    """Alertmanager webhook v4 body to (firing alerts, resolved fingerprints)."""
    if not isinstance(payload, dict) or not isinstance(payload.get('alerts'), list):
        raise ValueError('not an Alertmanager webhook payload')
    firing, resolved = [], []
    for raw in payload['alerts']:
        labels = raw.get('labels') or {}
        fingerprint = raw.get('fingerprint') or fingerprint_of(labels)
        if raw.get('status') == 'resolved':
            resolved.append(fingerprint)
            continue
        firing.append(
            Alert(
                fingerprint=fingerprint,
                alertname=labels.get('alertname', ''),
                severity=labels.get('severity', ''),
                target=target_of(labels),
                labels=labels,
                annotations=raw.get('annotations') or {},
                starts_at=parse_time(raw['startsAt']) if raw.get('startsAt') else 0.0,
            )
        )
    return firing, resolved

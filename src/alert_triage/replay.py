import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass

from alert_triage.models import Alert, target_of
from alert_triage.service import Service
from alert_triage.store import Store

GROUP_WAIT = 30


@dataclass
class Episode:
    labels: dict
    start: float
    end: float

    @property
    def fingerprint(self):
        return hashlib.sha1(json.dumps(sorted(self.labels.items())).encode()).hexdigest()[:16]

    def alert(self):
        return Alert(self.fingerprint, self.labels.get('alertname', ''), self.labels.get('severity', ''), target_of(self.labels), self.labels, {}, self.start)


def fetch_episodes(prometheus_url, days, step=120, flap_gap=600, now=None):
    """Firing episodes from the ALERTS series, with flaps shorter than flap_gap merged."""
    end = int(now or time.time())
    series = {}
    t = end - days * 86400
    while t < end:
        chunk_end = min(t + 7 * 86400, end)
        query = urllib.parse.urlencode({'query': 'ALERTS{alertstate="firing",alertname!="Watchdog"}', 'start': t, 'end': chunk_end, 'step': step})
        with urllib.request.urlopen(f'{prometheus_url.rstrip("/")}/api/v1/query_range?{query}', timeout=120) as response:
            for result in json.load(response)['data']['result']:
                labels = {k: v for k, v in result['metric'].items() if k != 'alertstate'}
                series.setdefault(tuple(sorted(labels.items())), (labels, []))[1].extend(v[0] for v in result['values'])
        t = chunk_end
    episodes = []
    for labels, stamps in series.values():
        stamps = sorted(set(stamps))
        start = prev = stamps[0]
        for stamp in stamps[1:]:
            if stamp - prev > flap_gap:
                episodes.append(Episode(labels, start, prev + step))
                start = stamp
            prev = stamp
        episodes.append(Episode(labels, start, prev + step))
    return sorted(episodes, key=lambda e: e.start)


class _ReplayAlertmanager:
    def __init__(self, episodes):
        self.episodes = episodes
        self.now = 0

    def active_fingerprints(self):
        return {e.fingerprint for e in self.episodes if e.start <= self.now < e.end}


class _ReplayMailer:
    def __init__(self):
        self.sent = []

    def send(self, subject, body):
        self.sent.append(subject)


def simulate(episodes, config):
    """Drives the real Service over historical episodes on a simulated clock; returns its recorded incidents."""
    clock = [0.0]
    alertmanager = _ReplayAlertmanager(episodes)
    mailer = _ReplayMailer()
    store = Store(':memory:')
    service = Service(config, store, alertmanager, mailer, clock=lambda: clock[0])
    arrivals = sorted(((e.start + GROUP_WAIT, e) for e in episodes), key=lambda x: x[0])

    def advance(until):
        while service.pending():
            nxt = clock[0] + config.tick_seconds
            if nxt > until:
                break
            clock[0] = alertmanager.now = nxt
            service.tick(nxt)

    for when, episode in arrivals:
        advance(when)
        clock[0] = alertmanager.now = when
        service.ingest([episode.alert()], when)
    advance(clock[0] + config.max_hold_seconds + config.debounce_seconds + config.tick_seconds)
    return store.incidents(), len(mailer.sent)


def report(episodes, incidents, days):
    outcomes = Counter(row[3] for row in incidents)
    weeks = days / 7
    lines = [
        f'episodes in scope: {len(episodes)}',
        f'incidents dispatched: {len(incidents)} ({len(incidents) / weeks:.1f}/week)',
        *[f'  {name}: {count}' for name, count in sorted(outcomes.items())],
        f'emails that would be sent: {outcomes.get("emailed", 0)} ({outcomes.get("emailed", 0) / weeks:.1f}/week)',
        f'alerts held back by cooldown (summed per incident): {sum(row[6] for row in incidents)}',
        'largest incidents:',
    ]
    for _id, opened, _dispatched, outcome, count, kept, _suppressed, detail in sorted(incidents, key=lambda r: -r[4])[:8]:
        names = Counter(a.split(' ')[0] for a in json.loads(detail)['alerts']).most_common(4)
        stamp = time.strftime('%m-%d %H:%M', time.localtime(opened))
        lines.append(f'  {stamp}  {count:3d} alerts ({kept} still firing) {outcome}: ' + ', '.join(f'{n} x{c}' for n, c in names))
    return '\n'.join(lines)

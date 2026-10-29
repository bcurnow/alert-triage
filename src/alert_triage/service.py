import logging
import threading
import time

from alert_triage import digest
from alert_triage.clusterer import Clusterer

log = logging.getLogger(__name__)


class Service:
    """Webhook alerts in, one digest per incident out.

    Pipeline: severity/ignore filter, cooldown, cluster, wait for quiet, confirm still firing, mail.
    """

    def __init__(self, config, store, alertmanager, mailer, clock=time.time):
        self.config = config
        self.store = store
        self.alertmanager = alertmanager
        self.mailer = mailer
        self.clock = clock
        self.clusterer = Clusterer(config.debounce_seconds, config.max_hold_seconds)
        self._suppressed = {}
        self._lock = threading.Lock()

    def restore(self):
        """Reload alerts that were waiting out the quiet period when the service last stopped."""
        with self._lock:
            for alert, arrived in self.store.load_pending():
                self.clusterer.add(alert, arrived)

    def pending(self):
        return len(self.clusterer)

    def ingest(self, firing, now=None):
        """Resolved notifications are deliberately not handled: whether an alert is still firing is decided
        against Alertmanager at dispatch, so a storm that clears before then is recorded, not lost."""
        now = self.clock() if now is None else now
        with self._lock:
            for alert in firing:
                if alert.severity not in self.config.severities or alert.alertname in self.config.ignore_alertnames:
                    continue
                if self.store.in_cooldown(alert.fingerprint, now, self.config.cooldown_seconds):
                    self._suppressed[alert.fingerprint] = alert
                elif self.clusterer.add(alert, now):
                    self.store.add_pending(alert, now)

    def tick(self, now=None):
        now = self.clock() if now is None else now
        with self._lock:
            incident = self.clusterer.due(now)
            suppressed = []
            if incident:
                for alert in incident.alerts:
                    self.store.remove_pending(alert.fingerprint)
                suppressed = list(self._suppressed.values())
                self._suppressed.clear()
        if incident:
            self._dispatch(incident, suppressed, now)
        return incident

    def _dispatch(self, incident, suppressed, now):
        check_failed = False
        try:
            active = self.alertmanager.active_fingerprints()
        except Exception:
            # Fail open: an unreachable Alertmanager must not hide an incident.
            log.exception('could not confirm which alerts are still firing; treating all as active')
            active, check_failed = None, True
        kept = incident.alerts if active is None else [a for a in incident.alerts if a.fingerprint in active]
        dropped = [a for a in incident.alerts if a not in kept]
        outcome = 'self_resolved'
        if kept or self.config.notify_self_resolved:
            subject, body = digest.render(incident, kept, dropped, suppressed, self.config.mail_subject_prefix, check_failed)
            try:
                self.mailer.send(subject, body)
                outcome = 'emailed' if kept else 'self_resolved'
            except Exception:
                log.exception('digest mail failed for incident %s', incident.id)
                outcome = 'mail_failed'
        if outcome == 'emailed':
            self.store.mark_dispatched(kept, now)
        detail = {'alerts': sorted(f'{a.alertname} {a.target}'.strip() for a in incident.alerts), 'check_failed': check_failed}
        self.store.record_incident(incident, now, outcome, kept, suppressed, detail)
        log.info('incident %s: %d alerts, %d still firing, %d suppressed, %s', incident.id, len(incident.alerts), len(kept), len(suppressed), outcome)

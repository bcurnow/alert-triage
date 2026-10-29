from dataclasses import dataclass


@dataclass
class Incident:
    id: str
    opened_at: float
    alerts: list


class Clusterer:
    """Collects alerts into one open incident and releases it once arrivals go quiet.

    Alertmanager groups by alertname, so a reboot storm arrives as dozens of groups; this is what turns
    them back into one thing to investigate. Time is passed in so the logic is deterministic under test.
    """

    def __init__(self, debounce, max_hold):
        self.debounce = debounce
        self.max_hold = max_hold
        self._alerts = {}
        self._opened = None
        self._last = None
        self._seq = 0

    def __len__(self):
        return len(self._alerts)

    def add(self, alert, now):
        """Returns False for an alert already pending; a repeat notification must not extend the quiet timer."""
        if alert.fingerprint in self._alerts:
            return False
        if not self._alerts:
            self._opened = now
        self._alerts[alert.fingerprint] = alert
        self._last = now
        return True

    def due(self, now):
        if not self._alerts:
            return None
        if now - self._last < self.debounce and now - self._opened < self.max_hold:
            return None
        incident = Incident(id=f'{int(self._opened)}-{self._seq}', opened_at=self._opened, alerts=list(self._alerts.values()))
        self._seq += 1
        self._alerts.clear()
        self._opened = self._last = None
        return incident

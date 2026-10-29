import json
import urllib.request


class AlertmanagerClient:
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def active_fingerprints(self):
        """Fingerprints still firing and neither silenced nor inhibited, i.e. worth investigating now."""
        url = f'{self.base_url}/api/v2/alerts?active=true&silenced=false&inhibited=false'
        with urllib.request.urlopen(url, timeout=self.timeout) as response:
            return {alert['fingerprint'] for alert in json.load(response)}

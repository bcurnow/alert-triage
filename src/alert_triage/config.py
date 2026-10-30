import tomllib
from dataclasses import dataclass, fields


@dataclass
class Config:
    listen_host: str = '127.0.0.1'
    listen_port: int = 9199
    alertmanager_url: str = 'https://alertmanager.internal.curnowtopia.com:9093'
    state_path: str = '/var/lib/alert-triage/state.db'
    # Alerts arriving within this much quiet time of each other are one incident.
    debounce_seconds: int = 300
    # A storm that never goes quiet is still dispatched after this long.
    max_hold_seconds: int = 1800
    # An alert (by Alertmanager fingerprint) already dispatched inside this window is not re-investigated.
    cooldown_seconds: int = 86400
    tick_seconds: int = 15
    severities: tuple = ('critical', 'warning')
    ignore_alertnames: tuple = ('Watchdog',)
    mail_sender: str = 'homelab@curnowtopia.com'
    mail_to: str = ''
    mail_subject_prefix: str = '[triage]'
    sendmail_command: tuple = ('msmtp', '-t')
    notify_self_resolved: bool = False


def load(path):
    with open(path, 'rb') as f:
        data = tomllib.load(f)
    known = {f.name: f for f in fields(Config)}
    unknown = set(data) - set(known)
    if unknown:
        raise ValueError(f'unknown config keys: {sorted(unknown)}')
    for name, value in data.items():
        if isinstance(known[name].default, tuple):
            data[name] = tuple(value)
    return Config(**data)

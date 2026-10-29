from collections import Counter
from datetime import datetime, timezone

_ORDER = {'critical': 0, 'warning': 1}


def _when(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def _counts(alerts):
    counts = Counter(a.alertname for a in alerts)
    return ', '.join(f'{name} x{count}' for name, count in sorted(counts.items()))


def render(incident, kept, dropped, suppressed, prefix, check_failed=False):
    """Plain-text digest. Phase 1 only lists what fired; no investigation happens yet."""
    names = sorted({a.alertname for a in kept})
    shown = ', '.join(names[:3]) + (f' (+{len(names) - 3} more)' if len(names) > 3 else '')
    subject = f'{prefix} {len(kept)} alert{"s" if len(kept) != 1 else ""}: {shown}' if kept else f'{prefix} resolved before dispatch: {len(dropped)} alert(s)'
    lines = [f'Incident {incident.id}, opened {_when(incident.opened_at)}', '(digest only: no investigation was performed)', '']
    if check_failed:
        lines += ['Alertmanager could not be queried to confirm these are still firing; all are listed.', '']
    by_severity = {}
    for alert in kept:
        by_severity.setdefault(alert.severity, {}).setdefault(alert.alertname, []).append(alert)
    for severity in sorted(by_severity, key=lambda s: _ORDER.get(s, 9)):
        lines.append(severity.upper())
        for name, alerts in sorted(by_severity[severity].items()):
            lines.append(f'  {name} ({len(alerts)})')
            for alert in sorted(alerts, key=lambda a: a.target):
                lines.append(f'    {alert.target or "(no target)"}  since {_when(alert.starts_at)}')
                summary = alert.annotations.get('summary') or alert.annotations.get('description')
                if summary:
                    lines.append(f'      {summary}')
        lines.append('')
    if dropped:
        lines += [f'No longer active at dispatch ({len(dropped)}): {_counts(dropped)}', '']
    if suppressed:
        lines += [f'Held back by the cooldown since the last digest ({len(suppressed)}): {_counts(suppressed)}', '']
    return subject, '\n'.join(lines).rstrip() + '\n'

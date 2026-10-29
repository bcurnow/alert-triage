# Alertmanager wiring

The service is one more Alertmanager webhook receiver. It must not change where existing alerts go, so
the route is added first and sets `continue: true`: Alertmanager keeps evaluating the routes below it.

```yaml
route:
  routes:
    - matchers:
        - severity=~"critical|warning"
      receiver: triage
      continue: true
      group_by: ['alertname']
      group_wait: 30s
      # ...the existing routes follow unchanged

receivers:
  - name: triage
    webhook_configs:
      - url: http://127.0.0.1:9199/webhook
        send_resolved: true
```

Notes:

- The service listens on loopback only, so there is no firewall rule and no TLS or token to manage.
- Grouping does not matter to the service: it merges alerts into incidents itself (a reboot storm
  arrives as one group per alertname). `send_resolved: true` is harmless; resolved notifications are
  ignored because whether an alert is still firing is checked against Alertmanager at dispatch.
- Alertmanager repeats a firing group every `repeat_interval`; the service dedups repeats by
  fingerprint, and the cooldown stops a long-running alert from producing a digest every few hours.

## Trying it without touching Alertmanager

`alert-triage replay` runs the real pipeline over the last N days of Prometheus alert history on a
simulated clock, with nothing sent, and prints how many incidents and emails that would have meant:

    .venv/bin/python -m alert_triage replay --days 30

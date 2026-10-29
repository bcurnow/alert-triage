# alert-triage

A background agent that receives Alertmanager webhooks, investigates the alert with read-only
tools, and emails a diagnosis with recommended next steps.

## Layout

Two systemd services on the monitoring host, running as separate unix users and talking over a
unix socket:

- **receiver/agent**: Alertmanager webhook, incident clustering and cooldown, Claude Agent SDK
  loop, email. Holds only the Anthropic API key.
- **tool server**: an MCP server exposing a small set of typed, read-only tools. Holds every
  infrastructure credential; the agent never sees them.

The agent has no built-in tools (no shell, no file access); it can only call the tool server.
Write-capable fixes, if ever added, live in a separate server with separate credentials and
propose-then-approve semantics.

## Development

    python3 -m venv .venv && . .venv/bin/activate
    pip install -e '.[dev]'
    pytest

## Status

Pre-implementation. The rollout plan (decisions, phases, firewall and ansible work, open
questions) is tracked in the infra repo:
<https://github.com/bcurnow/misc/blob/main/scripts/alert-triage/alert-triage-plan.md>

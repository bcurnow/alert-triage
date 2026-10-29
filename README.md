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

Everything installs into a project-local `.venv`; nothing goes on the host. On any host with
Python 3.12 or newer and `python3-venv`:

    make venv     # create .venv and install the project plus dev tooling
    make test
    make lint
    make format

`make help` lists the targets.

## Phase 1: digest service (no LLM)

`alert-triage serve --config config.toml` receives Alertmanager webhooks (see
[docs/alertmanager-route.md](docs/alertmanager-route.md)), clusters alerts into incidents, holds
back anything mailed recently, confirms with Alertmanager that the alerts are still firing, and
mails a plain-text digest. Pure standard library; state is a small SQLite file.

`alert-triage replay --days 30` runs the same pipeline over past Prometheus alert history to tune
the debounce and cooldown settings before anything goes live. Copy `config.example.toml` to start.

## Status

Phase 1 code complete and tested; not deployed. The rollout plan (decisions, phases, firewall and
ansible work, open questions) is tracked in the infra repo:
<https://github.com/bcurnow/misc/blob/main/scripts/alert-triage/alert-triage-plan.md>

## License

GPL-3.0. See [LICENSE](LICENSE).

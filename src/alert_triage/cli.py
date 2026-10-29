import argparse
import logging
import signal
import threading

from alert_triage import receiver, replay
from alert_triage.alertmanager import AlertmanagerClient
from alert_triage.config import Config, load
from alert_triage.mail import Mailer
from alert_triage.service import Service
from alert_triage.store import Store


def serve(args):
    config = load(args.config)
    if not config.mail_to:
        raise SystemExit('mail_to is required')
    service = Service(config, Store(config.state_path), AlertmanagerClient(config.alertmanager_url), Mailer(config.mail_sender, config.mail_to, config.sendmail_command))
    service.restore()
    server = receiver.make_server(service, config.listen_host, config.listen_port)
    stop = threading.Event()
    receiver.start_ticker(service, config.tick_seconds, stop)
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown).start())
    logging.getLogger(__name__).info('listening on %s:%s, %d alerts restored', config.listen_host, config.listen_port, service.pending())
    try:
        server.serve_forever()
    finally:
        stop.set()


def run_replay(args):
    config = load(args.config) if args.config else Config()
    episodes = [e for e in replay.fetch_episodes(args.prometheus_url, args.days) if e.labels.get('severity') in config.severities and e.labels.get('alertname') not in config.ignore_alertnames]
    incidents, _ = replay.simulate(episodes, config)
    print(replay.report(episodes, incidents, args.days))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='alert-triage')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('serve', help='run the webhook receiver')
    p.add_argument('--config', required=True)
    p.set_defaults(func=serve)
    p = sub.add_parser('replay', help='run the pipeline over past Prometheus alert history')
    p.add_argument('--prometheus-url', default='https://prometheus.internal.curnowtopia.com:9090')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--config')
    p.set_defaults(func=run_replay)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
    args.func(args)

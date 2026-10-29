import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from alert_triage.models import parse_webhook

log = logging.getLogger(__name__)
MAX_BODY = 1024 * 1024


def make_server(service, host, port):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status, body=b'{}'):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/healthz':
                self._reply(200, json.dumps({'pending': service.pending()}).encode())
            else:
                self._reply(404)

        def do_POST(self):
            if self.path != '/webhook':
                return self._reply(404)
            length = int(self.headers.get('Content-Length') or 0)
            if length > MAX_BODY:
                return self._reply(413)
            try:
                firing, _resolved = parse_webhook(json.loads(self.rfile.read(length)))
            except (ValueError, KeyError, TypeError):
                return self._reply(400)
            service.ingest(firing)
            self._reply(200)

        def log_message(self, fmt, *args):
            log.debug(fmt, *args)

    return ThreadingHTTPServer((host, port), Handler)


def start_ticker(service, interval, stop):
    def loop():
        while not stop.wait(interval):
            try:
                service.tick()
            except Exception:
                log.exception('tick failed')

    thread = threading.Thread(target=loop, name='ticker', daemon=True)
    thread.start()
    return thread

import http
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from threading import Thread

last_beat = time.time()
minimal_beat_time = 3600


def start_healthcheck(minimal_heartbeat_time: int, port: int = 5000):
    global minimal_beat_time
    minimal_beat_time = minimal_heartbeat_time

    httpd = http.server.HTTPServer(('', port), HealthCheck, False)
    httpd.server_bind()
    httpd.server_activate()

    def serve_forever(server):
        with server:  # to make sure httpd.server_close is called
            server.serve_forever()

    thread = Thread(target=serve_forever, args=(httpd,), daemon=True)
    thread.start()


def beat_healthcheck():
    global last_beat
    last_beat = time.time()


class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        global last_beat
        global minimal_beat_time

        current_time = time.time()
        if last_beat + minimal_beat_time < current_time:
            msg = f'Last beat was at {datetime.fromtimestamp(last_beat)}, ' \
                  f'current time {datetime.fromtimestamp(current_time)} ' \
                  f'and minimal heartbeat time is {minimal_beat_time}'
            self.reply(code=HTTPStatus.INTERNAL_SERVER_ERROR, message=msg)
        else:
            self.reply(message='Ok')

    def reply(self, code=HTTPStatus.OK, message: str = None):
        self.send_response(code)
        self.end_headers()
        if message:
            self.wfile.write(message.encode('utf-8'))

    def log_message(self, fmt, *args):
        return

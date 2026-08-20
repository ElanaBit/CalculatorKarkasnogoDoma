# -*- coding: utf-8 -*-
"""Dev-сервер для браузерного режима и самопроверки (?selftest)."""
import os, sys, json, time, threading, http.server, functools

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from api import Api

port = 8791
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'web')
reference = None
for name in os.listdir('.'):
    if name.lower().endswith('.xlsx') and not name.startswith('~$'):
        reference = os.path.abspath(name)
        break


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _send_json(self, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        route = self.path.split('?')[0]
        if route == '/data.json':
            self._send_json(Api().data)
            return
        if route == '/reference.xlsx' and reference and os.path.exists(reference):
            with open(reference, 'rb') as f:
                payload = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b''
        route = self.path.split('?')[0]
        try:
            body = json.loads(raw.decode('utf-8')) if raw else {}
        except Exception:
            body = {}
        try:
            api = Api()
            if route == '/upload':
                res = api.load_price_b64(body.get('b64', ''), body.get('filename', 'upload.xlsx'))
                self._send_json(res)
            elif route == '/export':
                res = api.export_estimate(body, save=False)
                self._send_json(res)
            elif route == '/update':
                res = api.update_price_from_url()
                self._send_json(res)
            else:
                self._send_json({'ok': False, 'message': 'Неизвестный маршрут'})
        except Exception as exc:
            self._send_json({'ok': False, 'message': str(exc)})


handler = functools.partial(Handler, directory=root)
server = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
print('SERVER_READY http://127.0.0.1:%d/index.html  reference=%s' % (port, reference))
sys.stdout.flush()
while True:
    time.sleep(60)

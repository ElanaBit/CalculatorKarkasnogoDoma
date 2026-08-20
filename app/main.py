# -*- coding: utf-8 -*-
"""Точка входа приложения «Калькулятор стоимости каркасного дома»."""
import os
import sys
import threading
import socketserver
import functools
import http.server
import webbrowser
import json

import webview

from api import Api


def resource_root():
    """Корень с ресурсами приложения (папка web)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def web_dir():
    return os.path.join(resource_root(), 'web')


def _free_port():
    with socketserver.socket.socket(socketserver.socket.AF_INET, socketserver.socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def _start_server():
    root = web_dir()

    class DataAwareHandler(QuietHandler):
        def _send_json(self, obj):
            payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path.split('?')[0] == '/data.json':
                from api import Api
                self._send_json(Api().data)
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
                from api import Api
                api = Api()
                if route == '/upload':
                    res = api.load_price_b64(body.get('b64', ''), body.get('filename', 'upload.xlsx'))
                    if res.get('ok'):
                        res['data'] = res['data']
                    self._send_json(res)
                elif route == '/export':
                    res = api.export_estimate(body, save=False)
                    self._send_json(res)
                else:
                    self._send_json({'ok': False, 'message': 'Неизвестный маршрут'})
            except Exception as exc:
                self._send_json({'ok': False, 'message': str(exc)})

    handler = functools.partial(DataAwareHandler, directory=root)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return f'http://127.0.0.1:{server.server_address[1]}/index.html'


def run_browser_mode():
    url = _start_server()
    webbrowser.open(url)
    print('Браузерный режим:', url)
    try:
        while True:
            threading.Event().wait(60)
    except KeyboardInterrupt:
        pass


def run_desktop_mode():
    index = os.path.join(web_dir(), 'index.html')
    if not os.path.exists(index):
        raise FileNotFoundError('index.html не найден в ресурсах приложения')
    api = Api()
    api.data_file = None
    window = webview.create_window(
        'Калькулятор стоимости каркасного дома',
        url=index,
        js_api=api,
        width=1500,
        height=920,
        min_size=(1120, 700),
        background_color='#0a0d14',
        text_select=False,
    )
    webview.start(gui='edgechromium')


def main():
    if '--browser' in sys.argv:
        run_browser_mode()
        return
    try:
        run_desktop_mode()
    except Exception as exc:  # webview/gui сбои → фолбэк в браузере
        print('Не удалось открыть окно приложения:', exc)
        print('Запускаем в браузере...')
        run_browser_mode()


if __name__ == '__main__':
    main()

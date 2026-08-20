# -*- coding: utf-8 -*-
import sys, os, io, json, base64, glob, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import main

url = main._start_server().replace('/index.html', '/')
print('server at', url)

def get(path):
    with urllib.request.urlopen(url + path) as r:
        return r.read()

html = get('index.html').decode('utf-8')
assert 'Калькулятор стоимости каркасного дома' in html, 'index не найден'
print('index.html OK, len=', len(html))

css = get('style.css').decode('utf-8')
assert 'topbar' in css
print('style.css OK, len=', len(css))

js = get('app.js').decode('utf-8')
assert 'init' in js
print('app.js OK, len=', len(js))

data = json.loads(get('data.json').decode('utf-8'))
print('data.json OK, items=', len(data['items']), 'sections=', len(data['sections']))

# upload endpoint
f = glob.glob('*.xlsx')[0]
raw = open(f, 'rb').read()
b64 = base64.b64encode(raw).decode('ascii')
req = urllib.request.Request(url + '/upload', data=json.dumps({'b64': b64, 'filename': f}).encode('utf-8'),
                             headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    res = json.loads(r.read().decode('utf-8'))
assert res['ok'], res
print('upload OK, items=', len(res['data']['items']))

# export endpoint
payload = {
    'params': {'area': 120},
    'items': [
        {'name': 'Тест', 'section': '1. Тест', 'subsection': '', 'unit': 'м²',
         'type': 'Работа', 'status': 'Обязательно', 'qty': 10, 'price': 500, 'amount': 5000}
    ],
}
req = urllib.request.Request(url + '/export', data=json.dumps(payload).encode('utf-8'),
                             headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    res = json.loads(r.read().decode('utf-8'))
assert res['ok'] and res['b64']
xlsx = base64.b64decode(res['b64'])
import openpyxl
wb = openpyxl.load_workbook(io.BytesIO(xlsx))
assert 'Смета' in wb.sheetnames
print('export OK, xlsx bytes=', len(xlsx))
print('ALL SERVER TESTS PASSED')

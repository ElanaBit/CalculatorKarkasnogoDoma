# -*- coding: utf-8 -*-
"""Проверка загрузки актуального справочника (xlsx) через мост pywebview в собранном exe."""
import json, time, urllib.request, websocket, sys

WS_URL = None
for attempt in range(40):
    try:
        with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=2) as r:
            targets = json.loads(r.read().decode('utf-8'))
        for t in targets:
            if t.get('type') == 'page':
                WS_URL = t['webSocketDebuggerUrl']
                break
        if WS_URL:
            break
    except Exception:
        pass
    time.sleep(0.5)

if not WS_URL:
    print('NO_CDP_TARGET')
    sys.exit(1)

ws = websocket.create_connection(WS_URL, timeout=20)
_id = 0


def call(method, params=None):
    global _id
    _id += 1
    ws.send(json.dumps({'id': _id, 'method': method, 'params': params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == _id:
            return msg.get('result', {})


def evaluate(expr):
    res = call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    if 'exceptionDetails' in res:
        return 'EXC: ' + json.dumps(res['exceptionDetails'], ensure_ascii=False)
    return res.get('result', {}).get('value')


call('Runtime.enable')

# ждём готовности моста
for i in range(30):
    if evaluate('typeof window.pywebview !== "undefined" && window.pywebview.api && typeof window.pywebview.api.load_price_file === "function"'):
        break
    time.sleep(0.5)

methods = evaluate('window.pywebview.api ? Object.keys(window.pywebview.api) : []')
print('api_methods:', methods)

path = sys.argv[1] if len(sys.argv) > 1 else ''
print('path:', path)

res = evaluate('(async function(){ try { var r = await window.pywebview.api.load_price_file(' + json.dumps(path) + '); return JSON.stringify({ok:r.ok, items:(r.data&&r.data.items&&r.data.items.length), sections:(r.data&&r.data.sections&&r.data.sections.length), src:r.source_file, msg:r.message}); } catch (e) { return "EXC " + String(e); } })()')
print('load_price_file:', res)

ws.close()
print('DONE')

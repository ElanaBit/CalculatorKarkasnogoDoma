# -*- coding: utf-8 -*-
"""Проверка кнопки «Обновить данные» в браузерном режиме (dev-сервер, fetch /update)."""
import json, time, urllib.request, websocket, sys

WS_URL = None
for attempt in range(60):
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

ws = websocket.create_connection(WS_URL, timeout=30)
ws.settimeout(0.3)
_id = 0
console_logs = []


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


def pump():
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get('method') == 'Runtime.consoleAPICalled':
                try:
                    args = [a.get('value', a.get('description', '')) for a in msg['params']['args']]
                    console_logs.append(msg['params']['type'] + ': ' + ' '.join(str(a) for a in args))
                except Exception:
                    pass
            if msg.get('method') == 'Runtime.exceptionThrown':
                console_logs.append('EXCEPTION: ' + json.dumps(msg['params'].get('exceptionDetails', {}), ensure_ascii=False)[:500])
    except Exception:
        return


call('Runtime.enable')

# ждём загрузки страницы (браузерный режим, без pywebview)
for i in range(60):
    pump()
    if evaluate('typeof state !== "undefined" && state.data'):
        break
    time.sleep(0.5)

print('page_ready items:', evaluate('state.data ? state.data.items.length : "none"'))
print('btn_update_exists:', evaluate('document.getElementById("btn-update") !== null'))
print('btn_order:', evaluate('(function(){ var a = document.getElementById("btn-update"), b = document.getElementById("btn-load"); return a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) ? "update-before-load" : "WRONG_ORDER"; })()'))

# кликаем по кнопке «Обновить данные» и ждём результат
evaluate('document.getElementById("btn-update").click()')
for i in range(90):
    pump()
    if evaluate('state.sourceFile'):
        break
    time.sleep(0.5)

print('after_click source:', evaluate('state.sourceFile'))
print('after_click items:', evaluate('state.items.length'))
print('chip:', evaluate('document.getElementById("data-chip-text").textContent'))
print('toast:', evaluate('var t = document.querySelectorAll(".toast"); t.length ? t[t.length-1].textContent : "none"'))
print('console_logs:', console_logs)

ws.close()
print('DONE')

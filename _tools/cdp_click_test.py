# -*- coding: utf-8 -*-
"""Нажимает кнопку «Загрузить данные» в собранном exe и собирает ошибки/события."""
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
events = []


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


def pump(dur):
    end = time.time() + dur
    while time.time() < end:
        try:
            msg = json.loads(ws.recv())
        except Exception:
            continue
        m = msg.get('method')
        if m in ('Runtime.exceptionThrown', 'Runtime.consoleAPICalled'):
            try:
                if m == 'Runtime.exceptionThrown':
                    d = msg['params']['exceptionDetails']
                    events.append('EXC: ' + (d.get('text', '') + ' :: ' + str(d.get('exception', {}).get('description', '')))[:400])
                else:
                    args = [a.get('value', a.get('description', '')) for a in msg['params']['args']]
                    events.append('LOG: ' + ' '.join(str(a) for a in args)[:400])
            except Exception:
                pass


call('Runtime.enable')
pump(1)

print('chip_class_before:', evaluate('document.getElementById("data-chip").className'))
print('clicking btn-load...')
call('Runtime.evaluate', {'expression': 'document.getElementById("btn-load").click()'})
pump(4)
print('chip_class_after:', evaluate('document.getElementById("data-chip").className'))
print('chip_text_after:', evaluate('document.getElementById("data-chip-text").textContent'))
print('toasts:', evaluate('Array.from(document.querySelectorAll(".toast")).map(function(t){return t.textContent}).join(" || ")'))
print('EVENTS:')
for e in events:
    print('  ', e)
ws.close()
print('DONE')

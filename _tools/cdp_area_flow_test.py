# -*- coding: utf-8 -*-
"""Естественный сценарий пользователя: загрузить прайс -> изменить площадь -> нажать «Начать расчет»."""
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

ws = websocket.create_connection(WS_URL, timeout=25)
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

for i in range(30):
    if evaluate('typeof window.pywebview !== "undefined" && window.pywebview.api && typeof window.pywebview.api.load_price_file === "function"'):
        break
    time.sleep(0.5)
for i in range(20):
    if evaluate('state.data === null && state.items.length === 0'):
        break
    time.sleep(0.5)

path = sys.argv[1] if len(sys.argv) > 1 else ''
evaluate('(async function(){ var r = await window.pywebview.api.load_price_file(' + json.dumps(path) + '); await handleLoadResult(r); })()')

print('after load, area=', evaluate('state.params.area'),
      '| qty first area-item=', evaluate('(function(){ var a=state.items.filter(function(c){return c.it.unit && c.it.unit.toLowerCase().indexOf("\u043f\u043b\u043e\u0449\u0430\u0434\u0438")>=0}); return a.length ? a[0].qty : "none"; })()'))

# меняем площадь ДО начала расчёта (реальный ввод)
evaluate('(function(){ var el = document.getElementById("area"); el.focus(); el.select(); })()')
call('Input.insertText', {'text': '160'})
time.sleep(1.0)
print('area after typing=160:', evaluate('state.params.area'),
      '| first area-item qty=', evaluate('(function(){ var a=state.items.filter(function(c){return c.it.unit && c.it.unit.toLowerCase().indexOf("\u043f\u043b\u043e\u0449\u0430\u0434\u0438")>=0}); return a[0].qty; })()'))

# жмём «Начать расчет»
evaluate('document.getElementById("btn-start").click()')
time.sleep(0.5)
print('after startCalc: included=', evaluate('state.totals.includedCount'),
      '| grand=', evaluate('Math.round(state.totals.grand)'),
      '| qty first area-item=', evaluate('(function(){ var a=state.items.filter(function(c){return c.it.unit && c.it.unit.toLowerCase().indexOf("\u043f\u043b\u043e\u0449\u0430\u0434\u0438")>=0}); return a[0].qty; })()'))

ws.close()
print('DONE')

# -*- coding: utf-8 -*-
"""Имитация реального ввода в поле площади через CDP Input + проверка DOM."""
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
evaluate('startCalc(); renderTotal();')

print('listener_attached:', evaluate('(function(){ var el = document.getElementById("area"); return typeof el.__listeners === "undefined" ? "n/a" : el.__listeners; })()'))

def snapshot(label):
    print(label, evaluate(
        '(function(){ var t = document.getElementById("total-amount").textContent;'
        'var f = document.getElementById("area").value;'
        'var q = []; var rows = document.querySelectorAll(".item-row .num-input.qty");'
        'var areaRows = []; document.querySelectorAll(".item").forEach(function(r){'
        '  var nameEl = r.querySelector(".item-name");'
        '  if (nameEl && nameEl.textContent.indexOf("\u041a\u0430\u0440\u043a\u0430\u0441") >= 0) {'
        '    var q = r.querySelector(".num-input.qty"); areaRows.push(q ? q.value : "none"); } });'
        'return JSON.stringify({field: f, total: t, areaRowQtys: areaRows}); })()'))

snapshot('STEP0 BEFORE:')

# фокус на поле и замена значения через настоящие события клавиатуры
evaluate('(function(){ var el = document.getElementById("area"); el.focus(); el.select(); })()')
call('Input.insertText', {'text': '180'})

# пауза, чтобы сработал input и анимации
time.sleep(1.2)

snapshot('STEP1 AFTER insertText 180:')

# также проверим состояние после ещё одного изменения вручную
evaluate('(function(){ var el = document.getElementById("area"); el.focus(); el.select(); })()')
call('Input.insertText', {'text': '95'})
time.sleep(1.2)
snapshot('STEP2 AFTER insertText 95:')

ws.close()
print('DONE')

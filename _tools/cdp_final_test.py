# -*- coding: utf-8 -*-
"""Финальная проверка собранного exe: старт без справочника, загрузка прайса, расчёт."""
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

# ждём готовности моста
for i in range(30):
    if evaluate('typeof window.pywebview !== "undefined" && window.pywebview.api && typeof window.pywebview.api.load_price_file === "function"'):
        break
    time.sleep(0.5)

# ждём завершения стартового init (пустое состояние)
for i in range(20):
    if evaluate('state.data === null && state.items.length === 0'):
        break
    time.sleep(0.5)

print('starts_empty:', evaluate('state.data === null && state.items.length === 0'))
print('chip_text:', evaluate('document.getElementById("data-chip-text").textContent'))
print('empty_state_rendered:', evaluate('document.querySelector(".empty-state") !== null'))
print('btn_load_bridge:', evaluate('typeof window.pywebview.api.choose_and_load_price === "function"'))

path = sys.argv[1] if len(sys.argv) > 1 else ''
res = evaluate('(async function(){ try { var r = await window.pywebview.api.load_price_file(' + json.dumps(path) + '); await handleLoadResult(r); return "loaded=" + state.items.length + " src=" + state.sourceFile; } catch (e) { return "EXC " + String(e); } })()')
print('load_apply:', res)

print('after_load_chip:', evaluate('document.getElementById("data-chip-text").textContent'))

print('startCalc_inc:', evaluate('(function(){ startCalc(); return state.items.filter(function(c){return c.included}).length; })()'))
print('recalc_grand:', evaluate('(function(){ recalc(); return Math.round(state.totals.grand); })()'))
print('total_modal:', evaluate('(function(){ openTotalModal(); return "hidden=" + document.getElementById("total-modal").hidden + " amount=" + document.getElementById("modal-total-amount").textContent; })()'))
print('newCalc:', evaluate('(function(){ newCalc(); return state.items.filter(function(c){return c.included}).length; })()'))

ws.close()
print('DONE')

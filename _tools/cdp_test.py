# -*- coding: utf-8 -*-
"""Проверка собранного exe через DevTools-протокол WebView2 (кнопки, мост pywebview)."""
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

console_logs = []


def on_msg(ws, message):
    msg = json.loads(message)
    if msg.get('method') == 'Runtime.consoleAPICalled':
        try:
            args = [a.get('value', a.get('description', '')) for a in msg['params']['args']]
            console_logs.append(msg['params']['type'] + ': ' + ' '.join(str(a) for a in args))
        except Exception:
            pass


ws.settimeout(0.2)
ws.sock.settimeout(0.2)

loaded = None
for i in range(30):
    try:
        msg = ws.recv()
        on_msg(ws, msg)
    except Exception:
        pass
    loaded = evaluate('typeof window.pywebview !== "undefined" && window.pywebview.api && typeof window.pywebview.api.init === "function"')
    if loaded is True:
        break
    time.sleep(0.5)

ws.settimeout(20)
ws.sock.settimeout(20)
print('BRIDGE_READY:', loaded)

time.sleep(2)

api_init_direct = evaluate('(async function(){ try { var r = await window.pywebview.api.init(); return "ok=" + r.ok + " items=" + (r.data && r.data.items.length) + " src=" + r.source_file + " sections=" + (r.data && r.data.sections.length); } catch (e) { return "EXC " + String(e); } })()')
print('api_init_direct:', api_init_direct)

manual_init = evaluate('(async function(){ try { await init(); return "init-done data=" + (state.data ? state.data.items.length : -1); } catch (e) { return "init-exc " + String(e); } })()')
print('manual_init:', manual_init)

checks = {
    'items_loaded': evaluate('typeof state !== "undefined" && state.data ? state.data.items.length : -1'),
    'buttons_bound': evaluate('(function(){ var b = document.getElementById("btn-start"); return b !== null; })()'),
    'toasts': evaluate('Array.from(document.querySelectorAll(".toast")).map(function(t){return t.textContent}).join(" || ")'),
}

console_logs2 = []
try:
    while True:
        console_logs2.append(console_logs.pop())
except Exception:
    pass
print('console_logs:', console_logs2)

print('startCalc_included:', evaluate('(function(){ startCalc(); return state.items.filter(function(c){return c.included}).length; })()'))
print('toast_container_exists:', evaluate('document.getElementById("toast-container") !== null'))
print('toast_count_after_startcalc:', evaluate('document.querySelectorAll(".toast").length'))
print('init_defined:', evaluate('typeof init'))
print('init_called_flag:', evaluate('(function(){ try { var g = document.getElementById("total-range"); return g ? g.textContent : "no-total-range"; } catch(e){ return "EXC"; } })()'))
print('state_data_null_reason:', evaluate('(function(){ var out=[]; out.push("data="+(state.data?"ok":"null")); out.push("items="+state.items.length); return out.join(" | "); })()'))
print('recalc_grand:', evaluate('(function(){ recalc(); return Math.round(state.totals.grand); })()'))
print('total_modal:', evaluate('(function(){ openTotalModal(); return "hidden=" + document.getElementById("total-modal").hidden + " amount=" + document.getElementById("modal-total-amount").textContent; })()'))
print('layout_bottom_actions:', evaluate('document.querySelectorAll(".totalbar #btn-start, .totalbar #btn-recalc, .totalbar #btn-new").length'))
print('layout_export_topbar:', evaluate('document.querySelectorAll(".topbar #btn-export").length'))
print('layout_total_left:', evaluate('document.querySelectorAll(".total-left #btn-total").length'))

for k, v in checks.items():
    print(k + ':', v)

ws.close()
print('DONE')

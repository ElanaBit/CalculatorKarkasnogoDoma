# -*- coding: utf-8 -*-
"""Проверка доступа к публичной таблице на Яндекс Диске."""
import json
import sys
import urllib.parse
import urllib.request

PUBLIC = 'https://disk.yandex.ru/i/FQUH4WtIbwH4ag'

sys.path.insert(0, 'app')
import price_parser

api_url = ('https://cloud-api.yandex.net/v1/disk/public/resources?public_key='
           + urllib.parse.quote(PUBLIC, safe=''))
print('GET', api_url)
req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
with urllib.request.urlopen(req, timeout=40) as r:
    info = json.loads(r.read().decode('utf-8'))
print('type:', info.get('type'), '| name:', info.get('name'), '| size:', info.get('size'))

if info.get('type') == 'dir':
    items = info.get('_embedded', {}).get('items', [])
    print('dir items:', [(i.get('name'), i.get('type'), i.get('size')) for i in items])
    target = next((i for i in items if i.get('type') == 'file'), None)
else:
    target = info
dl = (target or {}).get('file')
print('download_url head:', (dl or '')[:90])

if not dl:
    print('NO_DOWNLOAD_URL')
    sys.exit(1)

req2 = urllib.request.Request(dl, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req2, timeout=120) as r:
    raw = r.read()
print('downloaded bytes:', len(raw))
print('xlsx magic:', raw[:2], raw[:4])

parsed = price_parser.parse_bytes(raw, (target or {}).get('name', 'yadisk.xlsx'))
print('items:', len(parsed['items']), '| sections:', len(parsed['sections']), '| controls:', len(parsed['controls']))
print('meta:', parsed['meta'])
if parsed['items']:
    print('first item:', parsed['items'][0]['name'], '|', parsed['items'][0]['unit'], '| base=', parsed['items'][0]['base'])
print('DONE')

# -*- coding: utf-8 -*-
"""JS-API приложения: данные, загрузка прайса, экспорт сметы."""
import base64
import datetime
import json
import os
import urllib.parse
import urllib.request

import webview

import price_parser
import estimate_export


YANDEX_PUBLIC_URL = 'https://disk.yandex.ru/i/FQUH4WtIbwH4ag'
_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Calculator/1.0'


def _yadisk_download(public_url):
    """Скачивает публичный файл Яндекс Диска по ссылке-шарингу."""
    api = ('https://cloud-api.yandex.net/v1/disk/public/resources?public_key='
           + urllib.parse.quote(public_url, safe=''))
    with urllib.request.urlopen(
            urllib.request.Request(api, headers={'User-Agent': _USER_AGENT, 'Accept': 'application/json'}),
            timeout=40) as r:
        info = json.loads(r.read().decode('utf-8'))
    if info.get('type') == 'dir':
        items = info.get('_embedded', {}).get('items') or []
        target = next((i for i in items if i.get('type') == 'file'), None)
    else:
        target = info
    if not target:
        raise RuntimeError('на публичной ссылке не найден файл')
    dl = target.get('file')
    if not dl:
        raise RuntimeError('не удалось получить ссылку на скачивание')
    with urllib.request.urlopen(
            urllib.request.Request(dl, headers={'User-Agent': _USER_AGENT}), timeout=120) as r:
        raw = r.read()
    return raw, target.get('name') or 'spravochnik.xlsx'


class Api:
    def __init__(self):
        self.data = None
        self.data_file = None
        self._load_embedded()

    def _load_embedded(self):
        """Справочник позиций в приложение не встроен — загружается по кнопке «Загрузить данные»."""
        self.data = {
            'meta': {'source_file': None, 'items_total': 0, 'sections_total': 0,
                     'note': 'Справочник не загружен. Нажмите «Загрузить данные» и выберите файл прайса (xlsx).'},
            'items': [],
            'sections': [],
            'controls': [],
        }
        self.data_file = None

    def init(self):
        return {'ok': True, 'data': self.data, 'source_file': self.data_file, 'mode': 'app'}

    def get_data(self):
        return {'ok': True, 'data': self.data, 'source_file': self.data_file}

    def choose_and_load_price(self):
        """Нативный диалог выбора прайс-таблицы + разбор."""
        if not webview.windows:
            return {'ok': False, 'message': 'Нативный диалог недоступен.'}
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=('Справочник Excel (*.xlsx;*.xlsm)', 'Все файлы (*.*)'),
        )
        if not result:
            return {'ok': False, 'canceled': True}
        path = result if isinstance(result, str) else result[0]
        return self.load_price_file(path)

    def load_price_file(self, path):
        try:
            parsed = price_parser.parse(path)
        except Exception as exc:
            return {'ok': False, 'message': f'Не удалось прочитать файл: {exc}'}
        return self._apply_parsed(parsed, path)

    def load_price_b64(self, b64, filename='upload.xlsx'):
        try:
            raw = base64.b64decode(b64)
            parsed = price_parser.parse_bytes(raw, filename)
        except Exception as exc:
            return {'ok': False, 'message': f'Не удалось прочитать файл: {exc}'}
        return self._apply_parsed(parsed, filename)

    def update_price_from_url(self, public_url=None):
        """Скачивает актуальный прайс с Яндекс Диска и обновляет справочник."""
        try:
            raw, name = _yadisk_download(public_url or YANDEX_PUBLIC_URL)
            parsed = price_parser.parse_bytes(raw, name)
        except Exception as exc:
            return {'ok': False, 'message': f'Не удалось обновить данные с Яндекс Диска: {exc}'}
        res = self._apply_parsed(parsed, name)
        if res.get('ok'):
            res['message'] = ('Справочник обновлён с Яндекс Диска: ' + name
                              + ' · позиций: ' + str(len(parsed['items']))
                              + ', разделов: ' + str(len(parsed['sections'])) + '.')
        return res

    def _apply_parsed(self, parsed, source):
        if not parsed.get('items'):
            return {'ok': False,
                    'message': 'В файле не найдено позиций с ценами. Проверьте структуру: нужны столбцы «Наименование» и «Цена».'}
        if not parsed.get('controls'):
            parsed['controls'] = self.data.get('controls', [])
        self.data = parsed
        self.data_file = source
        return {
            'ok': True,
            'data': self.data,
            'source_file': source,
            'message': f'Загружено позиций: {len(parsed["items"])}. Разделов: {len(parsed["sections"])}.',
        }

    def export_estimate(self, payload, save=True):
        try:
            xlsx = estimate_export.build(payload)
        except Exception as exc:
            return {'ok': False, 'message': f'Ошибка формирования сметы: {exc}'}
        filename = f'Смета_каркасный_дом_{datetime.date.today().isoformat()}.xlsx'
        if save and webview.windows:
            result = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=filename,
                file_types=('Книга Excel (*.xlsx)',),
            )
            if not result:
                return {'ok': False, 'canceled': True}
            with open(result, 'wb') as f:
                f.write(xlsx)
            return {'ok': True, 'path': result, 'message': f'Смета сохранена:\n{result}'}
        return {'ok': True, 'b64': base64.b64encode(xlsx).decode('ascii'), 'filename': filename}

# -*- coding: utf-8 -*-
import glob, sys, io
import openpyxl
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

files = glob.glob('*.xlsx')
wb = openpyxl.load_workbook(files[0], data_only=True)

for ws in wb.worksheets:
    print('=' * 80)
    print('SHEET:', ws.title)
    for row in ws.iter_rows():
        vals = []
        for c in row:
            v = c.value
            if v is not None:
                vals.append(f'{c.coordinate}={v!r}')
        if vals:
            print(' | '.join(vals))

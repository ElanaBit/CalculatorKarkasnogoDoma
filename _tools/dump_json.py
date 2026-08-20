# -*- coding: utf-8 -*-
import glob, sys, io
import openpyxl
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

files = glob.glob('*.xlsx')
wb = openpyxl.load_workbook(files[0], data_only=True)
ws = wb.worksheets[0]

for row in ws.iter_rows(min_row=1, max_row=4):
    vals = []
    for c in row:
        if c.value is not None:
            vals.append(f'{c.coordinate}={c.value!r}')
    print(' | '.join(vals))
    print('-' * 40)

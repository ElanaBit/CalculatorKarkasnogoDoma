# -*- mode: python ; coding: utf-8 -*-
# Спецификация PyInstaller для сборки одного exe-файла приложения.
# Запуск: pyinstaller app.spec --noconfirm

app_name = 'КалькуляторКаркасногоДома'

a = Analysis(
    ['app/main.py'],
    pathex=['app'],
    binaries=[],
    datas=[
        ('app/web', 'web'),
        ('app/app.ico', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='app/app.ico',
)

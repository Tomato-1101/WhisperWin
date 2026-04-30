# -*- mode: python ; coding: utf-8 -*-
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [('src', 'src')]
binaries = []
hiddenimports = ['tzdata']

if sys.platform == "darwin":
    hiddenimports += [
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
    ]
elif sys.platform.startswith("win"):
    hiddenimports += [
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
    ]

# Collect silero_vad with all its data files
tmp_ret = collect_all('silero_vad')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Also collect silero_vad submodules explicitly
hiddenimports += collect_submodules('silero_vad')

# Collect PySide6 (only core modules needed)
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.scripts.deploy_lib'],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WhisperWin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WhisperWin',
)

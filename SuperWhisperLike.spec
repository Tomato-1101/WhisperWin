# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [('settings.yaml', '.')]
binaries = []
hiddenimports = [
    'faster_whisper',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'src.app',
    'src.main',
    'src.config',
    'src.config.types',
    'src.config.constants',
    'src.config.config_manager',
    'src.core',
    'src.core.audio_recorder',
    'src.core.transcriber',
    'src.core.input_handler',
    'src.ui',
    'src.ui.overlay',
    'src.ui.settings_window',
    'src.ui.system_tray',
    'src.utils',
    'src.utils.logger',
]

# Collect faster_whisper and ctranslate2 dependencies
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('ctranslate2')
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
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SuperWhisperLike',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

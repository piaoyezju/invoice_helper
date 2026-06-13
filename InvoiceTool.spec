# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('invoice_merger.py', '.'), ('auto_crop.py', '.'), ('icon.ico', '.'), ('icon.png', '.')],
    hiddenimports=[
        'invoice_merger', 'auto_crop',
        'fitz', 'fitz.fitz',
        'PIL', 'PIL._tkinter_finder',
        'cv2', 'cv2.cv2',
        'pyzbar', 'pyzbar.pyzbar',
        'numpy', 'numpy.core._methods',
    ],
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
    name='InvoiceTool',
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
    icon=['icon.ico'],
)

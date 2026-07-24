# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

base_path = Path(SPECPATH).resolve()

datas = []
binaries = []
hiddenimports = ['pandas_ta', 'ccxt', 'websockets', 'pandas_ta', 'ta', 'onnxruntime', 'sklearn', 'loguru', 'requests', 'secure_storage', 'Crypto.Cipher.AES', 'Crypto.Random']

for pkg in ["onnxruntime", "sklearn", "loguru", "pycryptodome"]:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas.extend(pkg_datas)
    binaries.extend(pkg_binaries)
    hiddenimports.extend(pkg_hidden)

datas.extend(collect_data_files('pandas_ta'))
datas.extend(collect_data_files('ta'))

model_path = base_path / "models" / "trading_model.onnx"
if model_path.exists():
    datas.append((str(model_path), "models"))

scaler_path = base_path / "models" / "scaler_params.json"
if scaler_path.exists():
    datas.append((str(scaler_path), "models"))

features_path = base_path / "models" / "feature_names.json"
if features_path.exists():
    datas.append((str(features_path), "models"))

logs_path = base_path / "logs"
if logs_path.exists():
    for f in logs_path.iterdir():
        if f.is_file():
            datas.append((str(f), "logs"))

version_info = base_path / "version_info.txt"

a = Analysis(
    ['main.py'],
    pathex=[str(base_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='trading_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_info) if version_info.exists() else None,
)

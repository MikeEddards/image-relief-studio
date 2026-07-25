# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


datas = collect_data_files("customtkinter")
datas += [
    ("LICENSE", "."),
    ("README.md", "."),
    ("IMAGE_GENERATION_GUIDE.md", "."),
]

hiddenimports = []
hiddenimports += collect_submodules("resvg_py")
hiddenimports += collect_submodules("trimesh.exchange")
hiddenimports += collect_submodules("trimesh.repair")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Installed only for the developer-side quality suite. Trimesh detects them
    # as optional integrations, but the desktop application does not use them.
    excludes=["pytest", "scipy"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageReliefStudio",
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
    version="windows_version_info.txt",
    icon="build_assets/app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ImageReliefStudio",
)

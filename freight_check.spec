# -*- mode: python ; coding: utf-8 -*-
"""Спецификация сборщика PyInstaller для настольного приложения «Рейс-Проверка»."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

PROJECT_ROOT = Path.cwd().resolve()
SRC_DIR = PROJECT_ROOT / "src"

# Сбор статических данных и ассетов приложения
datas = [
    (str(PROJECT_ROOT / "assets" / "icons"), "assets/icons"),
    (str(PROJECT_ROOT / "assets" / "styles"), "assets/styles"),
    (str(PROJECT_ROOT / "assets" / "models"), "assets/models"),
]

# Сбор обязательных данных сторонних библиотек
datas += collect_data_files("rapidocr_onnxruntime")
datas += collect_data_files("pypdfium2")
datas += collect_data_files("pypdfium2_raw")
datas += collect_data_files("docx")

# Сбор нативных динамических библиотек (DLL)
binaries = []
binaries += collect_dynamic_libs("pypdfium2_raw")
binaries += collect_dynamic_libs("onnxruntime")

# Скрытые импорты
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "rapidocr_onnxruntime",
    "pypdfium2",
    "pypdfium2_raw",
    "openpyxl",
    "xlrd",
    "docx",
    "pdfplumber",
    "rapidfuzz",
    "cv2",
    "PIL",
]
hiddenimports += collect_submodules("rapidocr_onnxruntime")
hiddenimports += collect_submodules("freight_check")

# Исключение неиспользуемых тяжелых модулей Qt и тестовых библиотек
excludes = [
    "tkinter",
    "unittest",
    "pytest",
    "basedpyright",
    "ruff",
    "pre_commit",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSpatialAudio",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
]

a = Analysis(
    [str(SRC_DIR / "freight_check" / "__main__.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# Очистка от неиспользуемых тяжелых бинарников Qt (DLL)
UNWANTED_DLL_PATTERNS = (
    "qt6qml",
    "qt6quick",
    "qt6webengine",
    "qt6multimedia",
    "qt63d",
    "qt6sensors",
    "qt6positioning",
    "qt6bluetooth",
    "qt6nfc",
    "qt6serial",
    "qt6sql",
    "qt6test",
    "qt6texttospeech",
    "qt6charts",
    "qt6datavisualization",
    "qt6designer",
    "qt6help",
    "qt6httpserver",
    "qt6pdf",
    "qt6spatialaudio",
    "qt6remoteobjects",
    "qt6scxml",
    "d3dcompiler",
    "opengl32sw",
)

filtered_binaries = []
for binary in a.binaries:
    dest_name = binary[0].lower()
    if any(pattern in dest_name for pattern in UNWANTED_DLL_PATTERNS):
        continue
    filtered_binaries.append(binary)

a.binaries = filtered_binaries

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="freight-check",
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
    icon=str(PROJECT_ROOT / "assets" / "icons" / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="freight-check",
)

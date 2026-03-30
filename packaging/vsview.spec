import importlib.metadata
import importlib.util
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from packaging.version import Version
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.splash import Splash
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)
from versioningit import get_version

ROOT_DIR = Path.cwd()
SRC_DIR = ROOT_DIR / "src"
MAIN_PATH = SRC_DIR / "vsview" / "__main__.py"
ICON_PATH = SRC_DIR / "vsview" / "assets" / "icon.png"
SPLASH_PATH = SRC_DIR / "vsview" / "assets" / "loading_hardcut.png"
# https://github.com/pyinstaller/pyinstaller/issues/8579

PLUGIN_ENTRY_POINT_GROUPS = ("vsview", "vsview.frameprops", "vsview.scening")
ONEFILE = os.getenv("VSVIEW_PYI_ONEFILE", "").lower() in {"1", "true", "yes", "on"}
APP_NAME = "VSView"
APP_VERSION = get_version(ROOT_DIR)
WINDOWS_VERSION_LANGUAGE_ID = 0x0409  # en-US
WINDOWS_VERSION_CODEPAGE = 1200  # UTF-16LE
WINDOWS_VERSION_STRING_TABLE = f"{WINDOWS_VERSION_LANGUAGE_ID:04X}{WINDOWS_VERSION_CODEPAGE:04X}"


def _installed_modules(*modules: str) -> set[str]:
    return {module for module in modules if importlib.util.find_spec(module) is not None}


def _icon_for_platform() -> str | None:
    # PyInstaller applies icons only on Windows and macOS.
    if sys.platform in {"win32", "darwin"} and ICON_PATH.exists():
        return str(ICON_PATH)

    return None


def _numeric_windows_version() -> Sequence[int]:
    version = Version(APP_VERSION)
    return (*version.release, version.post or 0)


def _windows_version_info() -> VSVersionInfo | None:
    if sys.platform != "win32":
        return None

    numeric_version = _numeric_windows_version()

    kid_version = StringFileInfo(
        [
            StringTable(
                WINDOWS_VERSION_STRING_TABLE,
                [
                    StringStruct("CompanyName", "Jaded Encoding Thaumaturgy"),
                    StringStruct("FileDescription", "The next-generation VapourSynth previewer"),
                    StringStruct("FileVersion", APP_VERSION),
                    StringStruct("InternalName", APP_NAME),
                    StringStruct("OriginalFilename", f"{APP_NAME}.exe"),
                    StringStruct("ProductName", APP_NAME),
                    StringStruct("ProductVersion", APP_VERSION),
                    StringStruct("LegalCopyright", "Copyright (c) 2026 Jaded Encoding Thaumaturgy"),
                ],
            )
        ]
    )

    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeric_version, prodvers=numeric_version),
        kids=[
            kid_version,
            VarFileInfo([VarStruct("Translation", [WINDOWS_VERSION_LANGUAGE_ID, WINDOWS_VERSION_CODEPAGE])]),
        ],
    )


def _collect_entry_points(hidden_imports: set[str], datas: set[tuple[str, str]]) -> None:
    copied_metadata = set[str]()

    for group in PLUGIN_ENTRY_POINT_GROUPS:
        for ep in importlib.metadata.entry_points(group=group):
            hidden_imports.add(ep.module)
            hidden_imports.update(collect_submodules(ep.module))
            datas.update(collect_data_files(ep.module))

            if ep.dist is None:
                continue

            dist_name = ep.dist.metadata.get("Name")
            if not dist_name or dist_name in copied_metadata:
                continue

            datas.update(copy_metadata(dist_name))
            copied_metadata.add(dist_name)


hidden_imports = set(collect_submodules("vsview"))
datas = set(collect_data_files("vsview.assets"))

hidden_imports.update(collect_submodules("vsview.app.tools"))
datas.update(collect_data_files("vsview.app.tools"))

_collect_entry_points(hidden_imports, datas)

hidden_imports.update({"PySide6.QtXml", "pydantic", "vapoursynth", "vsengine", "vspackrgb"})
hidden_imports.update(_installed_modules("keyring", "keyring.backends"))

if sys.platform == "win32":
    hidden_imports.update(_installed_modules("keyring.backends.Windows"))
elif sys.platform == "darwin":
    hidden_imports.update(_installed_modules("keyring.backends.macOS", "keyring.backends.macOS.api"))
else:
    hidden_imports.update(_installed_modules("keyring.backends.SecretService", "secretstorage", "jeepney"))

if ONEFILE:
    # PyInstaller's boot splash depends on Tk/Tcl
    hidden_imports.update(_installed_modules("tkinter", "_tkinter"))

excludes = ["niquests.extensions.pyodide", "pyodide"]

if sys.platform != "win32":
    excludes.append("wassima._os._windows")
    excludes.append("keyring.backends.Windows")
if sys.platform != "darwin":
    excludes.append("wassima._os._macos")
    excludes.extend(["keyring.backends.macOS", "keyring.backends.macOS.api"])
if sys.platform != "linux":
    excludes.append("wassima._os._linux")
    excludes.extend(["keyring.backends.SecretService", "secretstorage", "jeepney"])


a = Analysis(
    [MAIN_PATH],
    pathex=[SRC_DIR],
    binaries=[],
    datas=sorted(datas),
    hiddenimports=sorted(hidden_imports),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
)

pyz = PYZ(a.pure, a.zipped_data)

exe_args = [a.scripts]

if ONEFILE:
    exe_args.extend([a.binaries, a.zipfiles, a.datas])
    splash = Splash(
        SPLASH_PATH,
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(20, 355),
        text_size=10,
        text_color="white",
    )
    exe_args.append(splash)  # type: ignore[arg-type]


exe = EXE(
    pyz,
    *exe_args,
    exclude_binaries=not ONEFILE,
    name=APP_NAME,
    console=True,
    icon=_icon_for_platform(),
    version=_windows_version_info(),
)

if not ONEFILE:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        upx=True,
        upx_exclude=[],
        name=APP_NAME,
    )

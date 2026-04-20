# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for the Requirements Extractor GUI.
#
# Build with:
#     pyinstaller packaging/RequirementsExtractor.spec --clean --noconfirm
#
# This produces a single-file windowed executable at:
#     dist/RequirementsExtractor[.exe]
#
# The spec tries hard to include everything spaCy needs so the "--nlp"
# option works in the bundled app without any extra install step.  If you
# haven't installed spaCy + the English model into your build environment,
# the spec will still succeed but will silently skip those data files —
# the exe will then behave like a non-NLP build (graceful fallback).

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = []


def _bundle(pkg: str) -> None:
    """Pull every importable file/data asset from `pkg` into the build."""
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception as exc:  # pragma: no cover — best-effort collection
        print(f"[spec] warning: could not collect {pkg!r}: {exc}")


# Core runtime deps — always required.
_bundle("docx")          # python-docx ships a default template file
_bundle("openpyxl")

# Optional NLP stack — bundled so "Use NLP" works out of the box.
# If these aren't installed when you run the build, collect_all quietly
# returns nothing and the resulting exe falls back to non-NLP behaviour.
for _pkg in (
    "spacy",
    "en_core_web_sm",
    "thinc",
    "srsly",
    "cymem",
    "preshed",
    "murmurhash",
    "blis",
    "catalogue",
    "wasabi",
    "typer",
    "click",
    "pydantic",
    "pydantic_core",
    "annotated_types",
    "spacy_legacy",
    "spacy_loggers",
    "langcodes",
    "language_data",
    "marisa_trie",
    "weasel",
    "cloudpathlib",
    "smart_open",
    "confection",
):
    _bundle(_pkg)


a = Analysis(
    ["../run_gui.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "requirements_extractor",
        "requirements_extractor.gui",
        "requirements_extractor.cli",
        "requirements_extractor.extractor",
        "requirements_extractor.parser",
        "requirements_extractor.detector",
        "requirements_extractor.actors",
        "requirements_extractor.writer",
        "requirements_extractor.statement_set",
        "requirements_extractor.models",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim obvious bloat that none of our deps need.
        "matplotlib",
        "scipy",
        "numpy.distutils",
        "PIL.ImageTk",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "sphinx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="RequirementsExtractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX often triggers Windows AV false positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # --windowed: no background console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # set to "icon.ico" if you add one
)

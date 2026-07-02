"""Build a standalone CAT Regex Protector.exe with PyInstaller.

Usage:
    python build_exe.py

Output goes to dist/CAT Regex Protector.exe. custom_regex_rules.json (saved
custom rules) is written next to the exe at runtime; README.md and
Plural_form_regex.txt are bundled read-only inside the exe.
"""
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "CAT Regex Protector"
PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_DIR / "launcher.py"
ICON_PATH = PROJECT_DIR / "icon.ico"

DATA_FILES = ["README.md", "Plural_form_regex.txt"]


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Installing it now...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def build() -> None:
    ensure_pyinstaller()

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_POINT),
        "--name",
        APP_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(PROJECT_DIR / "dist"),
        "--workpath",
        str(PROJECT_DIR / "build"),
        "--specpath",
        str(PROJECT_DIR),
    ]

    for data_file in DATA_FILES:
        source = PROJECT_DIR / data_file
        if source.exists():
            args += ["--add-data", f"{source};."]
        else:
            print(f"Warning: {data_file} not found next to build_exe.py, skipping.")

    if ICON_PATH.exists():
        args += ["--icon", str(ICON_PATH)]

    subprocess.run(args, check=True, cwd=PROJECT_DIR)

    spec_file = PROJECT_DIR / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()

    exe_path = PROJECT_DIR / "dist" / f"{APP_NAME}.exe"
    print(f"\nBuild complete: {exe_path}")


if __name__ == "__main__":
    build()

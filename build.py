"""Build a standalone executable with PyInstaller.

    pip install pyinstaller
    python build.py

Produces dist/DashNdodge_Linux (or dist/DashNdodge_Windows.exe on Windows).
Executables only run on the OS they were built on, so build the Windows
version from Windows."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    name = "DashNdodge_Windows" if sys.platform.startswith("win") else "DashNdodge_Linux"
    if sys.platform == "darwin":
        name = "DashNdodge_macOS"
    sep = os.pathsep
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", name,
        "--icon", os.path.join(ROOT, "icon.ico"),
        "--add-data", f"{os.path.join(ROOT, 'fonts')}{sep}fonts",
        "--add-data", f"{os.path.join(ROOT, 'sprites')}{sep}sprites",
        "--add-data", f"{os.path.join(ROOT, 'vfx')}{sep}vfx",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", os.path.join(ROOT, "build"),
        os.path.join(ROOT, "main.py"),
    ]
    subprocess.check_call(args)
    for d in ("build", "dist"):
        path = os.path.join(ROOT, d, ".gitignore")
        with open(path, "w") as fh:
            fh.write("*\n")
    print(f"\nDone: dist/{name}{'.exe' if sys.platform.startswith('win') else ''}")


if __name__ == "__main__":
    main()

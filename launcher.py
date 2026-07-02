"""Entry point built into the .exe (see build_exe.py).

A --windowed PyInstaller build has no console, so an unhandled exception
during startup would otherwise just vanish silently. This wraps the real
app in a try/except that shows a message box instead.
"""
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

import RegexAssist


def main() -> None:
    try:
        RegexAssist.main()
    except Exception:
        details = traceback.format_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("CAT Regex Protector - Fatal Error", details)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

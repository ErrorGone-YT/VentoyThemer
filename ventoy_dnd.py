from __future__ import annotations

import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    DND_FILES = None
    DND_AVAILABLE = False

    class _FallbackTk(tk.Tk):
        pass

    class TkinterDnD:
        Tk = _FallbackTk

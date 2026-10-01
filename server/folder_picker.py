from __future__ import annotations

from pathlib import Path


def pick_directory(title: str, initial_dir: Path) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title=title, initialdir=str(initial_dir))
    finally:
        root.destroy()
    return Path(selected).resolve() if selected else None
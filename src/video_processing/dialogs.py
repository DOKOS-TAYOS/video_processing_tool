from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog


def _create_hidden_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def pick_input_file() -> Path | None:
    root = _create_hidden_root()
    try:
        selected = filedialog.askopenfilename(
            title="Selecciona el archivo de audio",
            filetypes=[
                ("Audio y video", "*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.mp4 *.mkv *.mov"),
                ("Todos los archivos", "*.*"),
            ],
        )
    finally:
        root.destroy()

    return Path(selected) if selected else None


def pick_output_directory() -> Path | None:
    root = _create_hidden_root()
    try:
        selected = filedialog.askdirectory(title="Selecciona la carpeta de salida")
    finally:
        root.destroy()

    return Path(selected) if selected else None

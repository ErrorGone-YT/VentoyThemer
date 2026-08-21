from __future__ import annotations

from pathlib import Path

import ventoy_support as support


def version_file_path() -> Path:
    return Path(support.resource_path("VentoyThemer", "version"))


def load_version(default: str = "Unknown (File not found)") -> str:
    path = version_file_path()
    try:
        if path.exists():
            version = path.read_text(encoding="utf-8").strip()
            return version or "Unknown (Empty File)"
        return default
    except Exception as exc:
        return f"Error loading version: {exc}"

from __future__ import annotations

import os
import shutil
import stat
import sys


def force_rmtree(path):
    """shutil.rmtree that clears read-only attributes, which are common in
    theme files copied from archives (Windows read-only bit, 0444 modes)."""
    def _clear_readonly(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_readonly)
    else:
        shutil.rmtree(path, onerror=_clear_readonly)


def find_theme_txt(root_dir):
    if not os.path.isdir(root_dir):
        return None

    for root, dirs, files in os.walk(root_dir):
        for name in files:
            # Themes ship "Theme.txt" / "THEME.TXT" as often as the exact
            # lowercase name, and the comparison must survive both.
            if name.lower() == "theme.txt":
                return os.path.join(root, name)
    return None


def find_pf2_fonts(root_dir, drive_root):
    fonts = set()
    if not os.path.isdir(root_dir) or not drive_root:
        return fonts

    for root, dirs, files in os.walk(root_dir):
        for file_name in files:
            if file_name.lower().endswith(".pf2"):
                try:
                    rel_path = os.path.relpath(os.path.join(root, file_name), drive_root).replace("\\", "/")
                    fonts.add(f"/{rel_path}")
                except ValueError:
                    continue

    return fonts

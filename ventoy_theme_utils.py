from __future__ import annotations

import os


def find_theme_txt(root_dir):
    if not os.path.isdir(root_dir):
        return None

    for root, dirs, files in os.walk(root_dir):
        if "theme.txt" in files:
            return os.path.join(root, "theme.txt")
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

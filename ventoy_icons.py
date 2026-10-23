"""GRUB boot-menu icon support for applied Ventoy themes.

GRUB shows a menu-entry icon only when the theme's boot_menu block declares
icon settings AND the theme ships matching PNG files in its icons/ folder
(next to the active theme.txt). Many themes ship icons without the settings,
so this module patches theme.txt after installation.
"""
from __future__ import annotations

import os
import re

_ICON_EXTENSIONS = (".png", ".jpg", ".jpeg")
_BOOT_MENU_RE = re.compile(r"^\s*\+\s*boot_menu\s*\{")
# GRUB treats a zero icon_width/icon_height/item_icon_space as "no icons",
# so a key explicitly set to 0 counts as absent (Ventoy's stock theme.txt
# ships `item_icon_space = 0`).
_PRESENCE_RES = {
    key: re.compile(r"^\s*{}\s*=".format(re.escape(key)))
    for key in ("icon_width", "icon_height", "item_icon_space")
}
_ZERO_RES = {
    key: re.compile(r"^(\s*{}\s*=\s*)0\s*$".format(re.escape(key)))
    for key in ("icon_width", "icon_height", "item_icon_space")
}
# Sensible defaults for a 1080p-sized theme; icons are scaled to this size.
_DEFAULT_VALUES = {"icon_width": "32", "icon_height": "32", "item_icon_space": "8"}


def find_icons_dir(theme_txt_path):
    """Return the icons directory GRUB searches for this theme, or None.

    GRUB resolves the icons folder relative to the directory holding the
    active theme.txt, so an icons/ folder elsewhere in the theme tree is
    ignored on purpose.
    """
    if not theme_txt_path or not os.path.isfile(theme_txt_path):
        return None
    icons_dir = os.path.join(os.path.dirname(theme_txt_path), "icons")
    return icons_dir if os.path.isdir(icons_dir) else None


def count_icon_files(icons_dir):
    total = 0
    for _root, _dirs, files in os.walk(icons_dir):
        total += sum(1 for name in files if name.lower().endswith(_ICON_EXTENSIONS))
    return total


def list_icon_classes(theme_txt_path):
    """Class names the theme can actually draw: the icons/ file basenames.

    GRUB renders menu entry icons from <class>.png files in the theme's
    icons folder, so this is exactly the set of classes worth offering
    to the user. None when the theme has no usable icons folder.
    """
    icons_dir = find_icons_dir(theme_txt_path)
    if icons_dir is None:
        return None
    classes = set()
    for root, _dirs, files in os.walk(icons_dir):
        for name in files:
            if name.lower().endswith(_ICON_EXTENSIONS):
                classes.add(os.path.splitext(name)[0])
    return sorted(classes) if classes else None


def ensure_boot_menu_icon_settings(theme_txt_path):
    """Make the boot_menu block of theme.txt actually show icons.

    Missing icon keys are added, and keys explicitly set to 0 (icons
    disabled) are re-enabled with default values; non-zero author values
    are respected. Returns the list of changed keys; an empty list means
    the block already enables icons, and None means there is no multi-line
    boot_menu block to configure. The file is rewritten only when something
    changed, and the original line endings/encoding are preserved.
    """
    if not theme_txt_path or not os.path.isfile(theme_txt_path):
        return None
    try:
        with open(theme_txt_path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    try:
        text, encoding = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = raw.decode("latin-1"), "latin-1"

    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)

    start = next((i for i, line in enumerate(lines) if _BOOT_MENU_RE.match(line)), None)
    if start is None:
        return None

    depth = 0
    close = None
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth <= 0:
            close = i
            break
    if close is None or close == start:
        # No closing brace, or a one-line block: nothing safe to patch.
        return None

    body = lines[start + 1:close]
    indent = ""
    for line in body:
        match = re.match(r"^(\s*)\w+\s*=", line)
        if match:
            indent = match.group(1)
            break

    changed = []
    for key in _DEFAULT_VALUES:
        zero_i = next(
            (i for i, line in enumerate(lines[start + 1:close], start=start + 1)
             if _ZERO_RES[key].match(line)),
            None,
        )
        if zero_i is not None:
            # Present but zero: re-enable in place, keeping the author's style.
            lines[zero_i] = _ZERO_RES[key].sub(
                lambda m: m.group(1) + _DEFAULT_VALUES[key], lines[zero_i])
        elif not any(_PRESENCE_RES[key].match(line) for line in body):
            # Absent: add next to the author's own properties.
            lines.insert(close, f"{indent or '  '}{key} = {_DEFAULT_VALUES[key]}")
            close += 1
        else:
            # Present with a non-zero value: respect the author's choice.
            continue
        changed.append(key)

    if not changed:
        return []

    try:
        with open(theme_txt_path, "wb") as f:
            f.write(eol.join(lines).encode(encoding))
    except OSError:
        return None
    return changed


def prepare_theme_icons(theme_dir, theme_txt_path):
    """Best-effort icon enablement for a freshly applied theme.

    Returns a summary dict {"icons": <file count>, "changed": [keys],
    "no_boot_menu": bool}; never raises, so theme installation can never
    fail because of this step.
    """
    summary = {"icons": 0, "changed": [], "no_boot_menu": False}
    try:
        icons_dir = find_icons_dir(theme_txt_path)
        if icons_dir is None:
            return summary
        summary["icons"] = count_icon_files(icons_dir)
        if summary["icons"] == 0:
            return summary
        changed = ensure_boot_menu_icon_settings(theme_txt_path)
        if changed is None:
            summary["no_boot_menu"] = True
        else:
            summary["changed"] = changed
    except Exception:
        summary = {"icons": 0, "changed": [], "no_boot_menu": False}
    return summary

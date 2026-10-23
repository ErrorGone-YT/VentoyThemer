"""Parse a GRUB theme.txt into data for a live HTML preview.

Only what a preview can reasonably approximate is extracted: the
desktop background, the boot_menu geometry/colors/icon sizing, pixmap
styles (rendered client-side as 9-slice composites), and the timeout
label. GRUB's pf2 bitmap fonts can't be used in a browser, so fonts
are reduced to a rough family + size guess.
"""
from __future__ import annotations

import os
import re

_PROP_RE = re.compile(r"^([\w-]+)\s*[:=]\s*(.+?)\s*$")
_COMPONENT_RE = re.compile(r"^\+\s*(\w+)\s*\{")

_IMAGE_EXTS = (".jpg", ".jpeg", ".png")

# "Unifont Regular 16" -> ("Unifont Regular", 16); fonts are bitmap pf2
# files a browser can't load, so only the size and a family guess survive.
_MONO_HINTS = ("mono", "fixed", "terminus", "unifont", "courier", "console")


def _split_font(value):
    parts = (value or "").rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        family, size = parts[0], int(parts[1])
    else:
        family, size = value or "", 16
    lower = family.lower()
    mono = any(h in lower for h in _MONO_HINTS)
    return {"family": "monospace" if mono else "sans-serif", "size": size, "raw": family}


def _geom(value):
    """'30%' -> ('%', 30.0); '42' -> ('px', 42.0); else None."""
    value = (value or "").strip()
    if value.endswith("%"):
        try:
            return ("%", float(value[:-1]))
        except ValueError:
            return None
    try:
        return ("px", float(value))
    except ValueError:
        return None


def _color(value):
    value = (value or "").strip()
    return value if re.match(r"^#[0-9a-fA-F]{3,8}$", value) else None


def parse_theme_txt(txt_path):
    """Return {global, components} parsed from theme.txt, or None."""
    if not txt_path or not os.path.isfile(txt_path):
        return None
    try:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None

    result = {"global": {}, "components": []}
    current = None
    depth = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current is None:
            component = _COMPONENT_RE.match(stripped)
            if component:
                current = {"type": component.group(1), "props": {}}
                depth = stripped.count("{") - stripped.count("}")
                result["components"].append(current)
            else:
                prop = _PROP_RE.match(stripped)
                if prop:
                    result["global"][prop.group(1)] = prop.group(2).strip('"')
            continue
        depth += stripped.count("{") - stripped.count("}")
        if depth <= 0:
            current = None
            depth = 0
            continue
        prop = _PROP_RE.match(stripped)
        if prop:
            current["props"][prop.group(1)] = prop.group(2).strip('"')
    return result


def build_preview_model(txt_path, drive):
    """Everything the JS preview needs, minus binary assets.

    Paths (background, pixmap styles) are returned relative to the drive
    so the caller can decide how to serve/inline them.
    """
    parsed = parse_theme_txt(txt_path)
    if parsed is None:
        return None
    theme_dir = os.path.dirname(os.path.abspath(txt_path))

    def rel_to_drive(path):
        if not path:
            return None
        root = os.path.normpath(drive)
        root_prefix = root.rstrip(os.sep) + os.sep
        if path.startswith("/"):
            # Already drive-relative (an applied wallpaper wallpaper path).
            full = os.path.normpath(os.path.join(root, path.lstrip("/")))
            if os.path.isfile(full):
                return path
            return None
        full = os.path.normpath(os.path.join(theme_dir, path))
        if full.lower().startswith(root_prefix.lower()):
            return "/" + os.path.relpath(full, root).replace("\\", "/")
        return None

    def find_image(pattern):
        if not pattern:
            return None
        if pattern.startswith("/"):
            full = os.path.normpath(os.path.join(drive, pattern.lstrip("/")))
            return full if os.path.isfile(full) else None
        if "*" in pattern:
            base, ext = os.path.splitext(pattern)
            prefix = base.split("*")[0]
            for name in sorted(os.listdir(theme_dir)):
                stem, file_ext = os.path.splitext(name)
                if file_ext.lower() == ext.lower() and stem.startswith(prefix):
                    return os.path.join(theme_dir, name)
            return None
        for ext in _IMAGE_EXTS:
            candidate = os.path.join(theme_dir, pattern)
            if os.path.isfile(candidate):
                return candidate
        candidate = os.path.join(theme_dir, pattern)
        return candidate if os.path.isfile(candidate) else None

    global_props = parsed["global"]
    menu = next((c["props"] for c in parsed["components"] if c["type"] == "boot_menu"), {})
    label = next((c["props"] for c in parsed["components"] if c["type"] == "label" and c["props"].get("id") == "__timeout__"), None)

    def geom(props, key, default=None):
        parsed_geom = _geom(props.get(key))
        return list(parsed_geom) if parsed_geom else default

    model = {
        "background": rel_to_drive(find_image(global_props.get("desktop-image"))),
        "desktop_color": _color(global_props.get("desktop-color")) or "#000000",
        "menu": {
            "left": geom(menu, "left", ("%", 15)),
            "top": geom(menu, "top", ("%", 25)),
            "width": geom(menu, "width", ("%", 70)),
            "height": geom(menu, "height", ("%", 50)),
            "item_color": _color(menu.get("item_color")) or "#cccccc",
            "selected_item_color": _color(menu.get("selected_item_color")) or "#ffffff",
            "icon_width": int(menu.get("icon_width", 32)),
            "icon_height": int(menu.get("icon_height", 32)),
            "item_icon_space": int(menu.get("item_icon_space", 8)),
            "item_height": int(menu.get("item_height", 36)),
            "item_spacing": int(menu.get("item_spacing", 8)),
            "item_padding": int(menu.get("item_padding", 4)),
            "menu_box": rel_to_drive(find_image(menu.get("menu_pixmap_style"))),
            "select_box": rel_to_drive(find_image(menu.get("selected_item_pixmap_style"))),
            "font": _split_font(menu.get("item_font")),
        },
        "label": None,
    }
    if label:
        model["label"] = {
            "text": label.get("text", ""),
            "color": _color(label.get("color")) or "#cccccc",
            "font": _split_font(label.get("font")),
            "left": geom(label, "left", ("%", 30)),
            "top": geom(label, "top", ("%", 85)),
            "width": geom(label, "width"),
            "align": label.get("align", "left"),
        }
    return model

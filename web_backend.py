"""JS bridge (pywebview js_api) for the web UI.

Every method is callable from JS as pywebview.api.<name>(...) and must
return JSON-serializable data. Long operations report progress through
window.backendEvent({stage, message, percent}) pushed with evaluate_js.

The pywebview Window is deliberately NOT an attribute of this object:
pywebview walks public attributes to build the JS bridge and a Window
attribute drags the whole native graph into it. It lives in _WINDOW.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import threading

import ventoy_config as ventoy_cfg
import ventoy_icons as icons_service
import ventoy_menu_class as menu_class_service
import ventoy_support as support
import ventoy_theme_preview as preview_service
import ventoy_theme_utils as theme_utils
import ventoy_translation as translation_service
from ventoy_archive import extract_theme_archive

RESOLUTIONS = ["max", "3840x2160", "2560x1440", "1920x1080", "1680x1050",
               "1600x900", "1440x900", "1280x1024", "1280x960", "1024x768", "800x600"]

_IMAGE_EXTS = (".zip", ".tar", ".tar.gz", ".tgz", ".xz", ".rar", ".7z", ".tar.bz2", ".tar.lz4", ".tar.zst")
_WALLPAPER_EXTS = (".png", ".jpg", ".jpeg")
VT_WALLPAPER_PREFIX = "/ventoy/wallpapers/"
VT_WALLPAPER_NAME = "vt-wallpaper"

_WINDOW = {"handle": None}


def attach_window(window):
    _WINDOW["handle"] = window


def _window():
    return _WINDOW["handle"]


def _file_data_url(path, max_bytes=12 * 1024 * 1024):
    if not path or not os.path.isfile(path) or os.path.getsize(path) > max_bytes:
        return None
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")


def _theme_txt_full(drive, theme_rel):
    return os.path.join(drive, theme_rel.lstrip("/").replace("/", os.sep))


def _install_name(source):
    """Folder name a theme is installed under (mirrors the Tk UI)."""
    base = os.path.basename(source.rstrip("\\/"))
    if os.path.isfile(source):
        base = os.path.splitext(base)[0]
    return base


class Api:
    def __init__(self):
        self.all_translations, default_messages = translation_service.load_translations()
        self.messages = translation_service.detect_language(self.all_translations) or default_messages

    # ---- plumbing -------------------------------------------------------

    def _(self, key, default=None):
        if key in self.messages:
            return self.messages[key]
        return default if default is not None else key

    def _notify(self, stage, message="", percent=None):
        window = _window()
        if window is None:
            return
        payload = json.dumps({"stage": stage, "message": message, "percent": percent}, ensure_ascii=False)
        try:
            window.evaluate_js(f"window.backendEvent({payload})")
        except Exception as e:
            print(f"notify failed: {e}")

    def get_i18n(self):
        detected = self.messages.get("name") if isinstance(self.messages, dict) else None
        return {"lang": detected, "messages": self.messages,
                "resolutions": RESOLUTIONS,
                "random_label": self._("option_random_theme", "Random Theme")}

    def get_languages(self):
        names = []
        for translation in self.all_translations:
            if isinstance(translation, dict) and translation.get("name"):
                names.append(translation["name"])
        return names

    def set_language(self, name):
        for translation in self.all_translations:
            if isinstance(translation, dict) and translation.get("name") == name:
                self.messages = translation
                return {"ok": True, "lang": name, "messages": self.messages}
        return {"ok": False}

    def open_link(self, url):
        import webbrowser

        if isinstance(url, str) and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            return True
        return False

    def ping(self):
        return "pong"

    # ---- drives & state -------------------------------------------------

    def list_drives(self):
        drives = support.list_available_drives()
        return [{
            "display": d.display,
            "root": d.root,
            "label": d.label,
            "ventoy": d.label.strip().lower() == "ventoy",
        } for d in drives]

    def load_theme_config(self, drive):
        json_path = os.path.join(drive, support.VENTOY_JSON_PATH)
        if not os.path.exists(json_path):
            return {}
        try:
            return ventoy_cfg.load_json_config(json_path)
        except Exception as e:
            print(f"ventoy.json read failed: {e}")
            return {}

    def save_theme_config(self, drive, config):
        ventoy_cfg.save_json_config(os.path.join(drive, support.VENTOY_JSON_PATH), config)

    def get_app_meta(self, config):
        value = config.get("ventoythemer")
        return value if isinstance(value, dict) else {}

    def _entry_name(self, entry):
        """Display name of a registered theme path: the dir holding
        theme.txt, or the folder itself for themeless packages."""
        parts = entry.strip("/").split("/")
        return parts[-2] if len(parts) >= 4 else (parts[2] if len(parts) == 3 else "")

    def _entry_folder(self, entry):
        """Installed folder: the component right after ventoy/theme/."""
        parts = entry.strip("/").split("/")
        return parts[2] if len(parts) >= 3 else ""

    def _revert_theme_overrides(self, config, drive, theme_key):
        """Restore a theme's original icons from its _originals/ backup
        and clear its override bookkeeping. Mutates the passed config;
        the caller is responsible for saving."""
        meta = self.get_app_meta(config)
        overrides = meta.get("theme_icon_overrides", {})
        entry = overrides.get(theme_key, {})
        backup_rel = entry.get("backup_dir", "")
        classes = entry.get("classes", [])
        if backup_rel and classes:
            backup_dir = os.path.normpath(os.path.join(drive, backup_rel.lstrip("/")))
            icons_dir = os.path.dirname(backup_dir)
            for cls in classes:
                restored = False
                for ext in (".png", ".jpg", ".jpeg"):
                    backup_file = os.path.join(backup_dir, cls + ext)
                    if os.path.isfile(backup_file):
                        os.replace(backup_file, os.path.join(icons_dir, cls + ext))
                        restored = True
                        break
                if not restored:
                    # No original existed: the copy was added by us.
                    for ext in (".png", ".jpg", ".jpeg"):
                        added = os.path.join(icons_dir, cls + ext)
                        if os.path.isfile(added):
                            os.remove(added)
        overrides.pop(theme_key, None)
        meta["theme_icon_overrides"] = overrides
        config["ventoythemer"] = meta

    def _apply_source_to_theme(self, drive, theme_key, source_tag):
        """Copy the icons of the currently assigned classes from
        source_tag into the theme's icons folder, preserving the theme's
        own icons in icons/_originals/."""
        import shutil

        config = self.load_theme_config(drive)
        if not source_tag:
            return {"ok": False, "copied": 0}
        source_dir = self._resolve_source_dir(config, drive, source_tag)
        if not source_dir or not os.path.isdir(source_dir):
            return {"ok": False, "error": "source icons not found"}

        files = config.get("theme", {}).get("file", []) or []
        theme_rel = next((e for e in files
                          if isinstance(e, str) and e.strip("/").startswith(theme_key.strip("/") + "/")), None)
        if not theme_rel:
            return {"ok": False, "error": "theme not registered"}
        theme_txt = _theme_txt_full(drive, theme_rel)
        icons_dir = icons_service.find_icons_dir(theme_txt) or os.path.join(os.path.dirname(theme_txt), "icons")
        os.makedirs(icons_dir, exist_ok=True)
        if os.path.normpath(icons_dir).lower() == os.path.normpath(source_dir).lower():
            return {"ok": True, "copied": 0}

        meta = self.get_app_meta(config)
        overrides = meta.setdefault("theme_icon_overrides", {})
        entry = dict(overrides.get(theme_key, {}))
        backup_dir = os.path.join(icons_dir, "_originals")
        os.makedirs(backup_dir, exist_ok=True)
        entry["backup_dir"] = "/" + os.path.relpath(backup_dir, drive).replace("\\", "/")

        classes = {rule["class"] for rule in menu_class_service.normalize_rules(config.get("menu_class"))}
        copied = 0
        touched = set(entry.get("classes", []))
        for cls in sorted(classes):
            source_file = next(
                (os.path.join(source_dir, cls + ext)
                 for ext in (".png", ".jpg", ".jpeg")
                 if os.path.isfile(os.path.join(source_dir, cls + ext))),
                None,
            )
            if not source_file:
                continue
            existing_target = next(
                (os.path.join(icons_dir, cls + ext)
                 for ext in (".png", ".jpg", ".jpeg")
                 if os.path.isfile(os.path.join(icons_dir, cls + ext))),
                None,
            )
            if existing_target:
                # Keep the theme's own icon so a revert can restore it.
                backup_file = os.path.join(backup_dir, os.path.basename(existing_target))
                if not os.path.isfile(backup_file):
                    os.replace(existing_target, backup_file)
                shutil.copy2(source_file, existing_target)
            else:
                shutil.copy2(source_file, os.path.join(icons_dir, cls + os.path.splitext(source_file)[1]))
            touched.add(cls)
            copied += 1
        entry["classes"] = sorted(touched)
        overrides[theme_key] = entry
        meta["theme_icon_overrides"] = overrides
        config["ventoythemer"] = meta
        self.save_theme_config(drive, config)
        return {"ok": True, "copied": copied}

    def sync_theme_icons(self, drive):
        """Re-apply every theme's stored icon source (after class rules
        or the source choice changed)."""
        config = self.load_theme_config(drive)
        meta = self.get_app_meta(config)
        for theme_key, source_tag in (meta.get("theme_icon_sources", {}) or {}).items():
            if not isinstance(source_tag, str):
                continue
            self._apply_source_to_theme(drive, theme_key, source_tag)

    def _cleanup_icon_meta(self, config, drive):
        """Drop stale icon-source bookkeeping: self-references, sources
        for unregistered themes, and override entries whose backup dirs
        no longer exist. Returns True when something was cleaned."""
        meta = self.get_app_meta(config)
        sources = meta.get("theme_icon_sources", {})
        overrides = meta.get("theme_icon_overrides", {})
        registered_folders = set()
        name_to_folder = {}
        for e in config.get("theme", {}).get("file", []) or []:
            if not isinstance(e, str) or not e:
                continue
            folder = self._entry_folder(e).lower()
            registered_folders.add(folder)
            name_to_folder[self._entry_name(e).lower()] = folder
        changed = False

        for key in list(sources):
            folder = key.rstrip("/").rsplit("/", 1)[-1].lower()
            tag = sources[key]
            if not tag.startswith("theme:"):
                continue  # pack: sources survive as-is
            target_folder = name_to_folder.get(tag[6:].lower())
            # Self-reference, or a source theme that no longer exists.
            if target_folder == folder or target_folder not in registered_folders:
                sources.pop(key, None)
                changed = True

        for key in list(overrides):
            folder = key.rstrip("/").rsplit("/", 1)[-1].lower()
            backup_rel = overrides[key].get("backup_dir", "")
            backup_abs = os.path.normpath(os.path.join(drive, backup_rel.lstrip("/")))
            if folder not in registered_folders or not os.path.isdir(backup_abs):
                overrides.pop(key, None)
                changed = True

        if changed:
            meta["theme_icon_sources"] = sources
            meta["theme_icon_overrides"] = overrides
            config["ventoythemer"] = meta
        return changed

    def get_state(self, drive):
        config = self.load_theme_config(drive)
        if self._cleanup_icon_meta(config, drive):
            self.save_theme_config(drive, config)
        theme = config.get("theme", {}) if isinstance(config, dict) else {}
        files = theme.get("file", []) or []
        names = [self._entry_name(p) for p in files if p]
        default_index = theme.get("default_file", 0)
        default_name = names[default_index - 1] if isinstance(default_index, int) and 1 <= default_index <= len(names) else ""
        meta = self.get_app_meta(config)
        folders = []
        for entry in files:
            if isinstance(entry, str) and entry:
                folders.append(self._entry_folder(entry))
        return {
            "theme_files": files,
            "theme_names": names,
            "theme_folders": sorted(set(folders)),
            "default_theme": default_name,
            "gfxmode": theme.get("gfxmode", "max"),
            "menu_class": menu_class_service.normalize_rules(config.get("menu_class")),
            "menu_class_mode": menu_class_service.read_menu_class(config)[0],
            "theme_icon_sources": meta.get("theme_icon_sources", {}),
            "icon_packs": self.list_icon_packs(drive),
            "wallpapers": self.list_wallpapers(drive),
            "theme_backgrounds": meta.get("theme_backgrounds", {}),
        }

    # ---- per-theme icon sources ------------------------------------------

    def set_icon_source(self, drive, theme_key, source_tag):
        """Attach source_tag ("theme:<Name>" / "pack:<Folder>") to one
        theme; empty tag (or the theme picking itself) reverts it to its
        own icons."""
        config = self.load_theme_config(drive)
        meta = self.get_app_meta(config)
        sources = meta.setdefault("theme_icon_sources", {})
        folder = theme_key.rstrip("/").rsplit("/", 1)[-1].lower()
        if (source_tag or "").lower() == "theme:" + folder:
            source_tag = ""  # theme picking itself = no override
        old_tag = sources.get(theme_key)
        if (old_tag or "") != (source_tag or ""):
            # Restore the theme's own icons before applying another source.
            self._revert_theme_overrides(config, drive, theme_key)
        if source_tag:
            sources[theme_key] = source_tag
        else:
            sources.pop(theme_key, None)
        meta["theme_icon_sources"] = sources
        config["ventoythemer"] = meta
        self.save_theme_config(drive, config)
        applied = self._apply_source_to_theme(drive, theme_key, source_tag)
        return {"ok": True, "copied": applied.get("copied", 0)}

    def _resolve_source_dir(self, config, drive, source_tag):
        """Icons dir for a source tag ("theme:<Name>" / "pack:<Folder>"),
        or None when the source does not exist."""
        if not source_tag or not isinstance(source_tag, str):
            return None
        if source_tag.startswith("pack:"):
            pack_dir = os.path.join(self.icon_packs_dir(drive), source_tag[5:])
            return pack_dir if os.path.isdir(pack_dir) else None
        if source_tag.startswith("theme:"):
            wanted = source_tag[6:].lower()
            for rel in config.get("theme", {}).get("file", []) or []:
                if isinstance(rel, str) and rel and \
                        self._entry_name(rel).lower() == wanted:
                    return icons_service.find_icons_dir(_theme_txt_full(drive, rel))
            return None
        return None

    def icon_packs_dir(self, drive):
        return os.path.join(drive, "ventoy", "iconpacks")

    def list_icon_packs(self, drive):
        packs_dir = self.icon_packs_dir(drive)
        if not os.path.isdir(packs_dir):
            return []
        return sorted(
            name for name in os.listdir(packs_dir)
            if os.path.isdir(os.path.join(packs_dir, name))
        )

    def add_icon_pack(self, drive, source_dir):
        # Copy a user folder with icon images into ventoy/iconpacks/.
        import shutil

        if not source_dir or not os.path.isdir(source_dir):
            return {"ok": False, "error": "folder not found"}
        images = [n for n in os.listdir(source_dir) if n.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            return {"ok": False, "error": "no images in folder"}
        packs_dir = self.icon_packs_dir(drive)
        os.makedirs(packs_dir, exist_ok=True)
        name = os.path.basename(os.path.normpath(source_dir))
        target = os.path.join(packs_dir, name)
        while os.path.exists(target):
            name += "-new"
            target = os.path.join(packs_dir, name)
        shutil.copytree(source_dir, target)
        return {"ok": True, "name": os.path.basename(target)}

    # ---- one-action icon set ----------------------------------------------

    def apply_icon_set(self, drive, theme_key, source_tag):
        """Single action for the combo: attach source_tag to the theme,
        auto-suggest classes for all images on the drive, merge them into
        menu_class, and copy the icons into the theme's icons folder.
        Empty source_tag reverts the theme to its own icons."""
        import shutil

        config = self.load_theme_config(drive)
        meta = self.get_app_meta(config)
        sources = meta.setdefault("theme_icon_sources", {})
        old_tag = sources.get(theme_key)
        if old_source := None or (old_tag or "") != (source_tag or ""):
            self._revert_theme_overrides(config, drive, theme_key)
        if source_tag:
            sources[theme_key] = source_tag
        else:
            sources.pop(theme_key, None)
        meta["theme_icon_sources"] = sources
        self.save_theme_config(drive, config)

        source_dir = self._resolve_source_dir(config, drive, source_tag)
        available = set()
        if source_dir and os.path.isdir(source_dir):
            for name in sorted(os.listdir(source_dir)):
                if name.lower().endswith((".png", ".jpg", ".jpeg")):
                    available.add(os.path.splitext(name)[0])

        files = menu_class_service.scan_image_files(drive)
        suggestions = {}
        for path in files:
            guess = menu_class_service.suggest_class(path)
            if guess and (not available or guess in available):
                suggestions[path] = guess

        final_rules = menu_class_service.merge_rules(
            menu_class_service.normalize_rules(config.get("menu_class")),
            suggestions, files)
        menu_class_service.write_menu_class(config, final_rules)
        self.save_theme_config(drive, config)

        copied = 0
        applied = self._apply_source_to_theme(drive, theme_key, source_tag)
        copied = applied.get("copied", 0)
        return {"ok": True, "rules": len(final_rules), "copied": copied, "suggested": len(suggestions)}

    # ---- images / icon classes ------------------------------------------

    def scan_images(self, drive, source_override=None):
        if not isinstance(source_override, str):
            source_override = None  # bridge garbage guard
        config = self.load_theme_config(drive)
        mode, rules = menu_class_service.read_menu_class(config)
        files = menu_class_service.scan_image_files(drive)
        base = {p: menu_class_service.effective_class(p, rules) for p in files}

        available = set()
        icons_dir = None
        source_dir = self._resolve_source_dir(config, drive, source_override)
        if source_dir and os.path.isdir(source_dir):
            for name in sorted(os.listdir(source_dir)):
                if name.lower().endswith((".png", ".jpg", ".jpeg")):
                    available.add(os.path.splitext(name)[0])
            icons_dir = source_dir
        else:
            # Fallback: the union of icons of every registered theme.
            for rel in config.get("theme", {}).get("file", []) or []:
                if not isinstance(rel, str) or not rel:
                    continue
                found = icons_service.find_icons_dir(_theme_txt_full(drive, rel))
                if found and os.path.isdir(found):
                    icons_dir = icons_dir or found
                    for name in sorted(os.listdir(found)):
                        if name.lower().endswith((".png", ".jpg", ".jpeg")):
                            available.add(os.path.splitext(name)[0])
        return {
            "files": files,
            "base": base,
            "available": sorted(available),
            "icons_dir": icons_dir,
        }

    def suggest_classes(self, files, available):
        suggestions = {}
        for path in files:
            guess = menu_class_service.suggest_class(path)
            if guess and (not available or guess in available):
                suggestions[path] = guess
        return suggestions

    def save_menu_class(self, drive, files, overrides, existing_rules):
        final_rules = menu_class_service.merge_rules(existing_rules, overrides, files)
        mode, _ = menu_class_service.read_menu_class(self.load_theme_config(drive))
        if mode == "multi":
            return {"ok": False, "error": "multi"}
        config = self.load_theme_config(drive)
        menu_class_service.write_menu_class(config, final_rules)
        self.save_theme_config(drive, config)
        self.sync_theme_icons(drive)
        return {"ok": True, "count": len(final_rules)}

    # ---- themes: install / remove / default / gfxmode --------------------

    def pick_sources(self):
        import webview

        window = _window()
        if window is None:
            return []
        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=("Theme Archives (*.zip;*.tar;*.tar.gz;*.tgz;*.xz;*.rar;*.7z;*.tar.zst)", "All files (*.*)"),
        )
        return list(result or [])

    def pick_image(self):
        import webview

        window = _window()
        if window is None:
            return ""
        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Images (*.png;*.jpg;*.jpeg)", "All files (*.*)"),
        )
        return (result or [""])[0]

    def pick_folder(self):
        import webview

        window = _window()
        if window is None:
            return ""
        result = window.create_file_dialog(webview.FileDialog.FOLDER)
        return (result or [""])[0]

    def register_dom_hooks(self):
        """Register the drag&drop handler through pywebview's DOM API.

        pywebview only captures real file paths when the drop listener is
        registered via window.dom (it then matches dropped files against
        paths collected by the WebView2 backend). Must run after the page
        has loaded (window.events.loaded).
        """
        from webview.dom import DOMEventHandler

        window = _window()
        if window is None or not sys.platform.startswith("win"):
            return  # real paths are only available on WebView2
        try:
            body = window.dom.get_element("body")
            body.events.drop += DOMEventHandler(
                self._on_drop_event, prevent_default=True, stop_propagation=True
            )
        except Exception as e:
            print(f"drop hook failed: {e}")

    def _on_drop_event(self, event):
        files = (event or {}).get("dataTransfer", {}).get("files", [])
        archives, images = [], []
        for file in files:
            path = file.get("pywebviewFullPath")
            if not path:
                continue
            lower = path.lower()
            if os.path.isfile(path) and lower.endswith(_IMAGE_EXTS):
                archives.append(path)
            elif os.path.isfile(path) and lower.endswith(_WALLPAPER_EXTS):
                images.append(path)
        window = _window()
        if window is None:
            return
        if archives:
            payload = json.dumps(archives, ensure_ascii=False)
            window.evaluate_js(f"window.addDroppedSources({payload})")
        if images:
            payload = json.dumps(images, ensure_ascii=False)
            window.evaluate_js(f"window.addDroppedWallpapers({payload})")

    def open_link(self, url):
        import webbrowser

        if isinstance(url, str) and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            return True
        return False

    def get_languages(self):
        names = []
        for translation in self.all_translations:
            if isinstance(translation, dict) and translation.get("name"):
                names.append(translation["name"])
        return names

    def set_language(self, name):
        for translation in self.all_translations:
            if isinstance(translation, dict) and translation.get("name") == name:
                self.messages = translation
                return {"ok": True, "lang": name, "messages": self.messages}
        return {"ok": False}

    def install_themes(self, drive, sources, decisions=None):
        """Install theme archives/folders.

        decisions maps source path -> "overwrite" (default) | "skip" |
        "copy" for themes that are already installed; "copy" picks a fresh
        <name>-2, <name>-3... folder.
        """
        decisions = decisions or {}
        total = len(sources)
        all_paths, all_fonts = set(), set()
        installed, skipped = [], []
        try:
            for i, source in enumerate(sources):
                name = _install_name(source)
                mode = decisions.get(source, "overwrite")
                percent = 100 * i // max(total, 1)
                theme_dir = os.path.join(drive, support.THEMES_DIR_NAME, name)
                if mode == "skip" and os.path.isdir(theme_dir):
                    skipped.append(name)
                    self._notify("install", self._("status_skipped_existing_theme", "Skipped existing theme: {}").format(name), percent)
                    continue

                target_name = name
                suffix = 1
                while mode == "copy" and os.path.isdir(os.path.join(drive, support.THEMES_DIR_NAME, target_name)):
                    suffix += 1
                    target_name = f"{name}-{suffix}"

                self._notify("install", self._("status_extracting", "Extracting {}...").format(target_name), percent)
                theme_dir = os.path.join(drive, support.THEMES_DIR_NAME, target_name)
                if os.path.isdir(theme_dir):
                    theme_utils.force_rmtree(theme_dir)
                os.makedirs(theme_dir, exist_ok=True)
                if os.path.isfile(source):
                    extract_theme_archive(source, theme_dir, translate=self._)
                else:
                    import shutil
                    shutil.copytree(source, theme_dir)

                txt = theme_utils.find_theme_txt(theme_dir)
                if txt:
                    all_paths.add("/" + os.path.relpath(txt, drive).replace("\\", "/"))
                else:
                    # No theme.txt anywhere (odd package): still register the
                    # folder so the user can see and remove it.
                    rel_dir = os.path.relpath(theme_dir, drive).replace("\\", "/")
                    all_paths.add("/" + rel_dir)
                    self._notify("install", self._("warning_theme_txt_not_found_message", "theme.txt not found in '{}'.").format(target_name), percent)
                all_fonts.update(theme_utils.find_pf2_fonts(theme_dir, drive))
                icons_service.prepare_theme_icons(theme_dir, txt)
                installed.append(target_name)

            config = self.load_theme_config(drive)
            ventoy_cfg.merge_theme_entries(config, all_paths, all_fonts)
            self.save_theme_config(drive, config)
            self.sync_theme_icons(drive)
            self._notify("done", self._("status_themes_applied_success", "Themes applied and config updated successfully!"), 100)
            return {"ok": True, "installed": installed, "skipped": skipped}
        except Exception as e:
            self._notify("error", str(e), 100)
            return {"ok": False, "error": str(e)}

    def remove_theme(self, drive, theme_name):
        """Delete an installed theme by its display name.

        The displayed name is the directory containing theme.txt, which is
        NOT necessarily the installed folder (a theme extracted from
        Vimix-1080p.tar shows as "Vimix" while living in
        ventoy/theme/Vimix-1080p.tar/...). The folder is therefore
        resolved from the registered ventoy.json path: it is the component
        directly under ventoy/theme/.
        """
        try:
            config = self.load_theme_config(drive)
            files = config.get("theme", {}).get("file", []) or []
            root_rel = None
            wanted = theme_name.lower()
            for entry in files:
                if not isinstance(entry, str) or not entry:
                    continue
                if self._entry_name(entry).lower() == wanted:
                    root_rel = "/".join(entry.strip("/").split("/")[:3])
                    break
            if root_rel:
                theme_root = os.path.normpath(os.path.join(drive, root_rel))
            else:
                theme_root = os.path.normpath(os.path.join(drive, support.THEMES_DIR_NAME, theme_name))

            if os.path.isdir(theme_root):
                theme_utils.force_rmtree(theme_root)

            normalized = theme_root.lower()

            def is_inside(path):
                if not path or not isinstance(path, str):
                    return False
                try:
                    full = os.path.normpath(os.path.join(drive, path.lstrip("/"))).lower()
                    return full.startswith(normalized + os.sep) or full == normalized
                except Exception:
                    return False

            ventoy_cfg.remove_theme_paths_from_config(config, is_inside)

            meta = self.get_app_meta(config)
            sources = meta.get("theme_icon_sources", {})
            overrides = meta.get("theme_icon_overrides", {})
            backgrounds = meta.get("theme_backgrounds", {})
            removed_folder = theme_root.rstrip(os.sep).rsplit(os.sep, 1)[-1].lower()
            removed_tag = "theme:" + theme_name.lower()
            removed_key = "/" + root_rel.strip("/")

            # Themes that took icons from the removed one fall back to
            # their own icons; the removed folder's own override and
            # wallpaper bookkeeping die with it.
            for theme_key, tag in list(sources.items()):
                if tag.lower() == removed_tag or                         theme_key.rstrip("/").rsplit("/", 1)[-1].lower() == removed_folder:
                    self._revert_theme_overrides(config, drive, theme_key)
                    sources.pop(theme_key, None)
            removed_prefix = "theme:" + theme_name.lower()
            for theme_key in list(overrides):
                key_folder = theme_key.rstrip("/").rsplit("/", 1)[-1].lower()
                if key_folder == removed_folder or theme_key.lower().startswith(removed_prefix):
                    overrides.pop(theme_key, None)
            backgrounds.pop(removed_key, None)

            meta["theme_icon_sources"] = sources
            meta["theme_icon_overrides"] = overrides
            meta["theme_backgrounds"] = backgrounds
            config["ventoythemer"] = meta

            # Last theme gone: give the user a truly clean config instead
            # of sections full of empty lists and stale assignments.
            if not config.get("theme", {}).get("file"):
                config.pop("menu_class", None)
                config.pop("ventoythemer", None)
            self.save_theme_config(drive, config)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_default_theme(self, drive, theme_name):
        config = self.load_theme_config(drive)
        theme = ventoy_cfg.ensure_theme_section(config)
        ventoy_cfg.update_default_theme(config, theme_name, theme.get("file", []),
                                        random_label=self._("option_random_theme", "Random Theme"))
        self.save_theme_config(drive, config)
        return {"ok": True}

    def set_gfxmode(self, drive, resolution):
        config = self.load_theme_config(drive)
        ventoy_cfg.update_gfxmode(config, resolution, RESOLUTIONS)
        self.save_theme_config(drive, config)
        return {"ok": True, "gfxmode": config["theme"]["gfxmode"]}

    # ---- wallpapers -------------------------------------------------------

    def wallpapers_dir(self, drive):
        return os.path.join(drive, "ventoy", "wallpapers")

    def list_wallpapers(self, drive):
        wp_dir = self.wallpapers_dir(drive)
        if not os.path.isdir(wp_dir):
            return []
        names = []
        for name in sorted(os.listdir(wp_dir)):
            if name.lower().endswith(_WALLPAPER_EXTS):
                names.append("/ventoy/wallpapers/" + name)
        return names

    def add_wallpaper(self, drive, source_path):
        import shutil
        import uuid

        if not source_path or not os.path.isfile(source_path):
            return {"ok": False, "error": "file not found"}
        if not source_path.lower().endswith(_WALLPAPER_EXTS):
            return {"ok": False, "error": "not an image"}
        wp_dir = self.wallpapers_dir(drive)
        os.makedirs(wp_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(source_path))[0]
        ext = os.path.splitext(source_path)[1].lower()
        target = os.path.join(wp_dir, base + ext)
        while os.path.exists(target):
            target = os.path.join(wp_dir, base + "-" + uuid.uuid4().hex[:6] + ext)
        shutil.copy2(source_path, target)
        return {"ok": True, "path": "/ventoy/wallpapers/" + os.path.basename(target)}

    def remove_wallpaper(self, drive, wallpaper_rel):
        # Revert any theme that currently uses this wallpaper first.
        config = self.load_theme_config(drive)
        meta = self.get_app_meta(config)
        maps = meta.get("theme_backgrounds", {})
        for theme_key, info in list(maps.items()):
            if isinstance(info, dict) and info.get("wallpaper") == wallpaper_rel:
                original = info.get("original") or ""
                if original:
                    self.set_theme_background(drive, theme_key, original)
                info["wallpaper"] = ""
                maps[theme_key] = info
        meta["theme_backgrounds"] = maps
        config["ventoythemer"] = meta

        path = os.path.normpath(os.path.join(drive, wallpaper_rel.lstrip("/")))
        wp_dir = os.path.normpath(self.wallpapers_dir(drive))
        if not path.startswith(wp_dir):
            return {"ok": False, "error": "outside wallpapers dir"}
        if os.path.isfile(path):
            os.remove(path)
        self.save_theme_config(drive, config)
        return {"ok": True}

    def set_theme_background(self, drive, theme_key, value):
        """Rewrite desktop-image in a registered theme.txt (theme_key is
        'ventoy/theme/<Folder>')."""
        import re as _re

        files = self.load_theme_config(drive).get("theme", {}).get("file", []) or []
        txt = None
        for entry in files:
            if isinstance(entry, str) and entry.strip("/").startswith(theme_key.strip("/") + "/"):
                txt = _theme_txt_full(drive, entry)
                break
        if txt is None:
            return {"ok": False, "error": "theme not registered"}
        try:
            with open(txt, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        for i, line in enumerate(lines):
            if _re.match(r"^\s*desktop-image\s*[:=]", line):
                lines[i] = _re.sub(
                    r"^(\s*desktop-image\s*[:=]\s*).*$",
                    lambda m: m.group(1) + '"' + value + '"',
                    line,
                )
                with open(txt, "w", encoding="utf-8", newline="") as f:
                    f.write("\n".join(lines))
                return {"ok": True}
        return {"ok": False, "error": "desktop-image line not found"}

    def apply_background(self, drive, theme_rel, wallpaper_rel):
        """Point the theme's desktop-image at a wallpaper (or revert with
        wallpaper_rel == ""). The original desktop-image value is kept in
        the ventoythemer meta so a revert restores it exactly."""
        import re as _re
        import shutil

        txt = _theme_txt_full(drive, theme_rel)
        if not os.path.isfile(txt):
            return {"ok": False, "error": "theme.txt not found"}
        theme_key = "/ventoy/theme/" + theme_rel.strip("/").split("/")[2]
        try:
            with open(txt, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError as e:
            return {"ok": False, "error": str(e)}

        line_index, current = None, None
        for i, line in enumerate(lines):
            match = _re.match(r"^\s*desktop-image\s*[:=]\s*(.+?)\s*$", line)
            if match:
                line_index, current = i, match.group(1).strip('"')
                break
        if line_index is None:
            return {"ok": False, "error": "desktop-image line not found"}

        config = self.load_theme_config(drive)
        meta = self.get_app_meta(config)
        maps = meta.setdefault("theme_backgrounds", {})
        info = dict(maps.get(theme_key, {}))

        theme_dir = os.path.dirname(txt)
        if wallpaper_rel:
            if not info.get("original"):
                info["original"] = "" if current.startswith(VT_WALLPAPER_PREFIX) else current
            # GRUB cannot resolve absolute paths in desktop-image (it aborts
            # with 'unaligned pointer' at boot), so the wallpaper is copied
            # INTO the theme folder and referenced by plain filename.
            source_file = os.path.normpath(os.path.join(drive, wallpaper_rel.lstrip("/")))
            ext = os.path.splitext(source_file)[1].lower()
            local_name = VT_WALLPAPER_NAME + ext
            shutil.copy2(source_file, os.path.join(theme_dir, local_name))
            info["wallpaper"] = wallpaper_rel
            info["local_name"] = local_name
            new_value = local_name
        else:
            for name in os.listdir(theme_dir):
                if name.startswith(VT_WALLPAPER_NAME) and                         name.lower().endswith(_WALLPAPER_EXTS):
                    os.remove(os.path.join(theme_dir, name))
            new_value = info.get("original") or current
            info["wallpaper"] = ""
        maps[theme_key] = info

        lines[line_index] = _re.sub(
            r"^(\s*desktop-image\s*[:=]\s*).*$",
            lambda m: m.group(1) + '"' + new_value + '"',
            lines[line_index],
        )
        try:
            with open(txt, "w", encoding="utf-8", newline="") as f:
                f.write("\n".join(lines))
        except OSError as e:
            return {"ok": False, "error": str(e)}

        meta["theme_backgrounds"] = maps
        config["ventoythemer"] = meta
        self.save_theme_config(drive, config)
        return {"ok": True, "value": new_value}

    # ---- preview ----------------------------------------------------------

    def get_preview(self, drive, theme_rel, gfxmode):
        txt = _theme_txt_full(drive, theme_rel)
        model = preview_service.build_preview_model(txt, drive)
        if model is None:
            return {"ok": False}
        try:
            width, height = (int(part) for part in gfxmode.lower().split("x"))
        except ValueError:
            width, height = 1280, 720

        theme_dir = os.path.dirname(txt)
        icons_dir = icons_service.find_icons_dir(txt)
        icons = {}
        if icons_dir:
            for name in sorted(os.listdir(icons_dir)):
                if name.lower().endswith(".png"):
                    data = _file_data_url(os.path.join(icons_dir, name), max_bytes=512 * 1024)
                    if data:
                        icons[os.path.splitext(name)[0]] = data

        def to_url(rel):
            return _file_data_url(os.path.join(drive, rel.lstrip("/").replace("/", os.sep))) if rel else None

        def pixmap_slices(box_rel):
            """'select' + select_{c,n,s,e,w,ne,nw,se,sw}.png -> suffix: dataURL."""
            if not box_rel:
                return {}
            base = os.path.splitext(os.path.basename(box_rel))[0]
            slices = {}
            for name in sorted(os.listdir(theme_dir)):
                stem, ext = os.path.splitext(name)
                if ext.lower() == ".png" and stem.startswith(base + "_"):
                    data = _file_data_url(os.path.join(theme_dir, name), max_bytes=512 * 1024)
                    if data:
                        slices[stem[len(base) + 1:]] = data
            return slices

        menu = model["menu"]
        menu["font"] = menu.get("font") or {"family": "sans-serif", "size": 16}
        menu["menu_slices"] = pixmap_slices(menu.get("menu_box"))
        menu["select_slices"] = pixmap_slices(menu.get("select_box"))
        return {
            "ok": True,
            "width": width,
            "height": height,
            "background": to_url(model.get("background")),
            "model": model,
            "icons": icons,
        }

from __future__ import annotations

import os

import ventoy_config as ventoy_cfg


def _safe_list_theme_folders(theme_dir):
    names = []
    if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
        try:
            names = [item for item in os.listdir(theme_dir) if os.path.isdir(os.path.join(theme_dir, item))]
        except PermissionError:
            return []
        except Exception:
            return []
    return names


def load_drive_theme_state(drive_root, random_label, select_theme_label, allowed_resolutions, themes_dir_name, ventoy_json_path):
    state = {
        "default_theme_values": [],
        "default_theme_value": random_label,
        "resolution_value": "",
        "remove_theme_values": [select_theme_label],
        "theme_display_names": [],
        "config": {},
    }

    if not drive_root:
        return state

    json_path = os.path.join(drive_root, ventoy_json_path)
    if os.path.exists(json_path):
        try:
            config = ventoy_cfg.load_json_config(json_path)
            state["config"] = config
            theme_config = config.get("theme", {})
            theme_files = theme_config.get("file", [])
            theme_display_names = [os.path.basename(os.path.dirname(p)) for p in theme_files if p and os.path.dirname(p)]
            state["theme_display_names"] = theme_display_names
            state["default_theme_values"] = [random_label, *theme_display_names]

            current_default_index = theme_config.get("default_file", 0)
            if current_default_index == 0:
                state["default_theme_value"] = random_label
            else:
                default_theme_name = ventoy_cfg.get_default_theme_name(theme_files, current_default_index)
                if default_theme_name and default_theme_name in theme_display_names:
                    state["default_theme_value"] = default_theme_name
                else:
                    state["default_theme_value"] = random_label

            current_resolution = theme_config.get("gfxmode", "max")
            state["resolution_value"] = current_resolution if current_resolution in allowed_resolutions else "max"

        except Exception:
            state["default_theme_value"] = random_label
            state["resolution_value"] = ""

    themes_disk_path = os.path.join(drive_root, themes_dir_name)
    state["remove_theme_values"].extend(_safe_list_theme_folders(themes_disk_path))
    return state

from __future__ import annotations

import json
import os


def load_json_config(json_path):
    if not os.path.exists(json_path):
        return {}

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_config(json_path, config):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def ensure_theme_section(config):
    config.setdefault("theme", {})
    theme_config = config["theme"]
    theme_config.setdefault("file", [])
    theme_config.setdefault("default_file", 0)
    theme_config.setdefault("gfxmode", "max")
    theme_config.setdefault("display_mode", "GUI")
    theme_config.setdefault("serial_param", "--unit=0 --speed=9600")
    theme_config.setdefault("fonts", [])
    theme_config.setdefault("images", [])
    return theme_config


def get_theme_names_from_files(theme_files):
    return [os.path.basename(os.path.dirname(p)) for p in theme_files if p and os.path.dirname(p)]


def get_default_theme_name(theme_files, default_index_1_based):
    if not theme_files or default_index_1_based <= 0:
        return ""
    if default_index_1_based > len(theme_files):
        return ""

    path_in_json = theme_files[default_index_1_based - 1]
    if not path_in_json:
        return ""
    return os.path.basename(os.path.dirname(path_in_json)) if os.path.dirname(path_in_json) else ""


def merge_theme_entries(config, theme_paths, font_paths):
    theme_config = ensure_theme_section(config)
    theme_config["file"] = sorted(list(set(theme_config.get("file", [])) | set(theme_paths)))
    theme_config["fonts"] = sorted(list(set(theme_config.get("fonts", [])) | set(font_paths)))
    return config


def update_default_theme(config, selected_theme, theme_files, random_label="Random Theme"):
    theme_config = ensure_theme_section(config)

    if selected_theme == random_label:
        theme_config["default_file"] = 0
        return config

    if selected_theme and selected_theme in get_theme_names_from_files(theme_files):
        target_suffix_txt = f"/{selected_theme}/theme.txt"
        target_suffix_dir = f"/{selected_theme}"
        index_in_json = -1

        for i, path_value in enumerate(theme_files):
            if not path_value or not isinstance(path_value, str):
                continue
            normalized_value = path_value.lower().replace("\\", "/")
            if normalized_value.endswith(target_suffix_txt.lower()) or normalized_value == target_suffix_dir.lower():
                index_in_json = i
                break

        theme_config["default_file"] = index_in_json + 1 if index_in_json != -1 else 0
        return config

    theme_config["default_file"] = 0
    return config


def update_gfxmode(config, resolution, allowed_resolutions):
    theme_config = ensure_theme_section(config)
    if resolution in allowed_resolutions:
        theme_config["gfxmode"] = resolution
    elif theme_config.get("gfxmode") not in allowed_resolutions:
        theme_config["gfxmode"] = "max"
    return config


def remove_theme_paths_from_config(config, predicate):
    theme_config = ensure_theme_section(config)
    theme_config["file"] = [p for p in theme_config.get("file", []) if not predicate(p)]
    theme_config["fonts"] = [p for p in theme_config.get("fonts", []) if not predicate(p)]
    theme_config["images"] = [p for p in theme_config.get("images", []) if not predicate(p)]

    current_default_index = theme_config.get("default_file", 0)
    if current_default_index > len(theme_config.get("file", [])):
        theme_config["default_file"] = 0
    return config


def clear_theme_entries(config):
    theme_config = ensure_theme_section(config)
    theme_config["file"] = []
    theme_config["fonts"] = []
    theme_config["images"] = []
    theme_config["default_file"] = 0
    return config

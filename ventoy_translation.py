from __future__ import annotations

import json
import os

import ventoy_support as support
import ventoy_version as version_service


def load_translations():
    translation_file_path = support.resource_path("VentoyThemer", "languages.json")
    all_translations = []
    messages = {}

    try:
        if os.path.exists(translation_file_path):
            with open(translation_file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            if isinstance(loaded_data, list) and loaded_data:
                all_translations = loaded_data
                if isinstance(all_translations[0], dict):
                    messages = all_translations[0]
                else:
                    messages = {}
            else:
                all_translations = []
                messages = {}
    except Exception:
        all_translations = []
        messages = {}

    return all_translations, messages


def load_version():
    return version_service.load_version()

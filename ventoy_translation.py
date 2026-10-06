from __future__ import annotations

import json
import locale
import os
import re

import ventoy_support as support
import ventoy_version as version_service


# ISO language codes -> English name prefix used in languages.json
# ("Russian (Русский)", ...). Covers the languages shipped with the app.
ISO_LANGUAGE_NAMES = {
    "ar": "Arabic", "az": "Azerbaijani", "be": "Belarusian", "bg": "Bulgarian",
    "bn": "Bengali", "ca": "Catalan", "ceb": "Cebuano", "cs": "Czech",
    "da": "Danish", "de": "German", "el": "Greek", "en": "English",
    "es": "Spanish", "fa": "Persian", "fi": "Finnish", "fil": "Tagalog",
    "fr": "French", "gl": "Galician", "ha": "Hausa", "hi": "Hindi",
    "hr": "Croatian", "hu": "Hungarian", "hy": "Armenian", "id": "Indonesian",
    "in": "Indonesian", "it": "Italian", "ja": "Japanese", "ka": "Georgian",
    "ko": "Korean", "lt": "Lithuanian", "mk": "Macedonian", "ms": "Malay",
    "nb": "Norwegian Bokmål", "nl": "Dutch", "no": "Norwegian",
    "nn": "Norwegian", "oc": "Occitan", "pl": "Polish", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sk": "Slovak", "sl": "Slovenian",
    "sr": "Serbian", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil",
    "th": "Thai", "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian",
    "ur": "Urdu", "vi": "Vietnamese", "zh": "Chinese",
}


def _locale_tokens():
    tokens = []
    for raw in (os.environ.get("LC_ALL"), os.environ.get("LANG"), None):
        if raw is None:
            try:
                raw = locale.getlocale()[0] or ""
            except Exception:
                raw = ""
        if raw and raw.lower() not in ("c", "posix"):
            tokens.append(raw)
    return tokens


def _find_language(all_translations, token):
    if not token:
        return None
    token = token.strip()
    if not token:
        return None
    # "ru_RU.UTF-8" -> "ru"; "Russian_Russia" -> "russian"
    base = re.split("[_@.+-]", token)[0].lower()
    for candidate in {token.lower(), base}:
        english_name = ISO_LANGUAGE_NAMES.get(candidate)
        if not english_name:
            # Windows-style locale names ("Russian_Russia") match directly.
            english_name = candidate
        prefix = english_name.lower()
        for lang in all_translations:
            if isinstance(lang, dict):
                name = str(lang.get("name", "")).lower()
                if name.startswith(prefix + " (") or name == prefix:
                    return lang
    return None


def detect_language(all_translations):
    """Return the translation matching the OS locale, or None to keep the
    default (the first language in languages.json)."""
    if not all_translations:
        return None
    for token in _locale_tokens():
        matched = _find_language(all_translations, token)
        if matched:
            return matched
    return None


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

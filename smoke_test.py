"""Headless smoke test of core (non-UI) services. Prints PASS/FAIL lines."""
import os
import sys
import tempfile
import traceback
import zipfile

failures = []


def _zip_roundtrip():
    import ventoy_archive as archive_service

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "t.zip")
        with zipfile.ZipFile(src, "w") as z:
            z.writestr("theme/theme.txt", "test-content")
        out = os.path.join(tmp, "out")
        os.makedirs(out)
        archive_service.extract_theme_archive(src, out)
        extracted = open(os.path.join(out, "theme", "theme.txt")).read()
        assert extracted == "test-content", extracted
        return "zip ok"


def _config_roundtrip():
    import ventoy_config as config_service

    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "cfg.json")
        config_service.save_json_config(cfg, {"test_key": "test_value"})
        loaded = config_service.load_json_config(cfg)
        assert loaded.get("test_key") == "test_value", loaded
        return "config ok"


import ventoy_version as version_service
import ventoy_translation as translation_service
import ventoy_support as support
import ventoy_drive_service as drive_service


def check(name, fn):
    try:
        result = fn()
        print(f"PASS {name}: {result}")
    except Exception:
        failures.append(name)
        print(f"FAIL {name}")
        traceback.print_exc()


check("import all modules", lambda: [
    m for m in (
        "ventoy_support", "ventoy_config", "ventoy_archive", "ventoy_drive_service",
        "ventoy_translation", "ventoy_version", "ventoy_theme_utils", "ventoy_theme_jobs",
        "ventoy_input_handlers", "ventoy_app_helpers", "ventoy_ui_helpers", "ventoy_tab_ui",
        "ventoy_language_ui", "ventoy_dnd",
    ) if __import__(m) is not None
])
check("version loads", lambda: version_service.load_version(default="EMPTY"))
check("translations load", lambda: f"{len(translation_service.load_translations()[0])} languages")
check("locale detect", lambda: (translation_service.detect_language(translation_service.load_translations()[0]) or {}).get("name", "none"))
check("resource_path", lambda: support.resource_path("VentoyThemer", "languages.json")[-20:])
check("zip extract (roundtrip)", _zip_roundtrip)
check("config load/save", _config_roundtrip)
check("drive listing", lambda: f"{len(support.list_drives_display())} drives found")

print("---")
print("RESULT:", "ALL PASS" if not failures else f"FAILURES: {failures}")
sys.exit(1 if failures else 0)

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


def _icons_roundtrip():
    import ventoy_icons as icons_service

    with tempfile.TemporaryDirectory() as tmp:
        theme = os.path.join(tmp, "MyTheme")
        icons = os.path.join(theme, "icons")
        os.makedirs(icons)
        for name in ("ubuntu.png", "windows.png", "sub/vtoyiso.png"):
            path = os.path.join(icons, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()
        theme_txt = os.path.join(theme, "theme.txt")
        with open(theme_txt, "w", newline="") as f:
            f.write('+ boot_menu {\n  left = 10%\n  item_font = "Unknown Regular 16"\n}\n')

        info = icons_service.prepare_theme_icons(theme, theme_txt)
        assert info["icons"] == 3, info
        assert sorted(info["changed"]) == ["icon_height", "icon_width", "item_icon_space"], info
        patched = open(theme_txt).read()
        assert "icon_width = 32" in patched and "item_icon_space = 8" in patched, patched
        assert patched.index("item_icon_space") < patched.index("}"), patched

        # Second run: settings complete, nothing changed.
        info2 = icons_service.prepare_theme_icons(theme, theme_txt)
        assert info2["changed"] == [], info2

        # A fully configured theme.txt must stay byte-identical.
        before = open(theme_txt, "rb").read()
        icons_service.prepare_theme_icons(theme, theme_txt)
        assert open(theme_txt, "rb").read() == before

        # CRLF files keep their line endings.
        theme_crlf = os.path.join(tmp, "CrlfTheme")
        os.makedirs(os.path.join(theme_crlf, "icons"))
        open(os.path.join(theme_crlf, "icons", "vtoyiso.png"), "wb").close()
        theme_crlf_txt = os.path.join(theme_crlf, "theme.txt")
        with open(theme_crlf_txt, "w", newline="") as f:
            f.write("+ boot_menu {\r\n  left = 0%\r\n}\r\n")
        info3 = icons_service.prepare_theme_icons(theme_crlf, theme_crlf_txt)
        assert len(info3["changed"]) == 3, info3
        crlf_patched = open(theme_crlf_txt, "rb").read()
        assert b"\r\n  icon_width = 32\r\n" in crlf_patched, crlf_patched

        # Keys explicitly set to 0 (Ventoy's stock theme.txt style) are
        # re-enabled in place instead of duplicated.
        theme_zero = os.path.join(tmp, "ZeroTheme")
        os.makedirs(os.path.join(theme_zero, "icons"))
        open(os.path.join(theme_zero, "icons", "vtoyiso.png"), "wb").close()
        theme_zero_txt = os.path.join(theme_zero, "theme.txt")
        with open(theme_zero_txt, "w", newline="") as f:
            f.write("+ boot_menu {\n  left = 0%\n  item_icon_space = 0\n}\n")
        info4 = icons_service.prepare_theme_icons(theme_zero, theme_zero_txt)
        assert sorted(info4["changed"]) == ["icon_height", "icon_width", "item_icon_space"], info4
        zero_patched = open(theme_zero_txt).read()
        assert zero_patched.count("item_icon_space") == 1, zero_patched
        assert "item_icon_space = 8" in zero_patched and "item_icon_space = 0" not in zero_patched, zero_patched

        # Theme without icons dir: reported as zero, file untouched.
        theme_bare = os.path.join(tmp, "BareTheme")
        os.makedirs(theme_bare)
        bare_txt = os.path.join(theme_bare, "theme.txt")
        with open(bare_txt, "w", newline="") as f:
            f.write("+ boot_menu {\n  left = 0%\n}\n")
        info5 = icons_service.prepare_theme_icons(theme_bare, bare_txt)
        assert info5 == {"icons": 0, "changed": [], "no_boot_menu": False}, info5
        assert "icon_width" not in open(bare_txt).read()
        return "patched, idempotent, CRLF-safe, zero-fixing, no-op without icons"


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
def _menuclass_logic():
    import ventoy_menu_class as mc

    with tempfile.TemporaryDirectory() as tmp:
        for p in ("Win11_25H2_English.iso", "ubuntu-26.04.iso", "ventoy/theme/x.iso", "tool.wim"):
            fp = os.path.join(tmp, *p.split("/"))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "wb").close()
        files = mc.scan_image_files(tmp)
        assert "ventoy/theme/x.iso" not in files and len(files) == 3, files

        rules = [{"key": "Win11", "class": "windows"}]
        assert mc.effective_class("Win11_25H2_English.iso", rules) == "windows"
        assert mc.effective_class("ubuntu-26.04.iso", rules) == "vtoyiso"
        assert mc.effective_class("tool.wim", rules) == "vtoywim"
        assert mc.suggest_class("ubuntu-26.04.iso") == "ubuntu"

        final = mc.merge_rules(rules, {"ubuntu-26.04.iso": "ubuntu"}, files)
        assert final[0] == {"key": "ubuntu-26.04", "class": "ubuntu"}, final
        assert {"key": "Win11", "class": "windows"} in final
        final2 = mc.merge_rules(rules, {"Win11_25H2_English.iso": ""}, files)
        assert {"key": "Win11", "class": "windows"} not in final2
        assert mc.read_menu_class({"menu_class": {"legacy": []}})[0] == "multi"
        # Ventoy requires the key to be strictly shorter than the file
        # name (patlen < namelen in ventoy_plugin.c) — a key equal to the
        # full file name silently never matches.
        rule = mc.build_rule("Win11_25H2_English_x64_v2.iso", "windows")
        assert rule["key"] == "Win11_25H2_English_x64_v2", rule
        assert len(rule["key"]) < len("Win11_25H2_English_x64_v2.iso")

        import ventoy_icons as icons_service
        with tempfile.TemporaryDirectory() as t2:
            theme = os.path.join(t2, "T")
            os.makedirs(os.path.join(theme, "icons", "sub"))
            for n in ("windows.png", "ubuntu.PNG", "readme.txt"):
                open(os.path.join(theme, "icons", n), "wb").close()
            open(os.path.join(theme, "icons", "sub", "arch.jpg"), "wb").close()
            txt = os.path.join(theme, "theme.txt")
            open(txt, "w").close()
            classes = icons_service.list_icon_classes(txt)
            assert classes == ["arch", "ubuntu", "windows"], classes
            assert icons_service.list_icon_classes(os.path.join(t2, "nope.txt")) is None
        return "scan/effective/merge/multimode/short-key/icon-classes ok"


check("zip extract (roundtrip)", _zip_roundtrip)
check("config load/save", _config_roundtrip)
check("icons patch (roundtrip)", _icons_roundtrip)
check("menu class logic", _menuclass_logic)
check("drive listing", lambda: f"{len(support.list_drives_display())} drives found")

print("---")
print("RESULT:", "ALL PASS" if not failures else f"FAILURES: {failures}")
sys.exit(1 if failures else 0)

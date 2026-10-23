"""Ventoy menu_class management: scan image files on a drive, resolve the
effective boot-menu class per file, and read/write the menu_class array
(top level of ventoy.json).

Ventoy semantics (ventoy.net/en/plugin_menuclass.html):
- "key" is a case-sensitive substring matched against the file NAME only;
- "parent" matches files directly inside that directory (no trailing slash);
- "dir" matches files under that directory path;
- the FIRST matching rule in the array wins;
- files no rule matches get a built-in class by extension (iso -> vtoyiso).
"""
from __future__ import annotations

import os
import posixpath

IMAGE_EXTENSIONS = (".iso", ".img", ".wim", ".efi", ".vhd", ".vhdx", ".vtoy")
SKIPPED_TOP_DIRS = {"ventoy", "System Volume Information", "$RECYCLE.BIN"}

# Built-in classes Ventoy assigns when no menu_class rule matches.
_BUILT_IN_BY_EXTENSION = {
    ".iso": "vtoyiso",
    ".wim": "vtoywim",
    ".img": "vtoyimg",
    ".efi": "vtoyefi",
    ".vhd": "vtoyvhd",
    ".vhdx": "vtoyvhd",
    ".vtoy": "vtoyvtoy",
}

# Substring (lowercase, checked against the file name) -> suggested class.
# Ordered: first hit wins, so "win11" is checked before generic "windows".
SUGGEST_PATTERNS = (
    ("win11", "windows"), ("win_11", "windows"), ("win10", "windows"),
    ("win_10", "windows"), ("win8", "windows"), ("win7", "windows"),
    ("winxp", "windows"), ("windows", "windows"),
    ("install.wim", "windows"),
    ("ubuntu", "ubuntu"), ("kubuntu", "kubuntu"), ("xubuntu", "xubuntu"),
    ("lubuntu", "lubuntu"), ("mint", "linuxmint"), ("debian", "debian"),
    ("manjaro", "manjaro"), ("arch", "arch"), ("endeavouros", "endeavouros"),
    ("fedora", "fedora"), ("centos", "centos"), ("rocky", "rocky"),
    ("almalinux", "almalinux"), ("opensuse", "opensuse"), ("suse", "opensuse"),
    ("kali", "kali"), ("zorin", "zorin"), ("elementary", "elementary"),
    ("pop_os", "pop"), ("pop-os", "pop"), ("gentoo", "gentoo"),
    ("void", "void"), ("alpine", "alpine"), ("nixos", "nixos"),
    ("slackware", "slackware"), ("deepin", "deepin"), ("redos", "redos"),
    ("altlinux", "alt"), ("astra", "astra"),
)

# Sentinel: the user never touched this file's class in the UI.
UNSET = object()


def scan_image_files(drive):
    """Return sorted image-file paths relative to drive, '/'-separated."""
    results = []
    drive = os.path.normpath(drive)
    for root, dirs, files in os.walk(drive):
        rel_root = os.path.relpath(root, drive).replace("\\", "/")
        top = rel_root.split("/", 1)[0]
        if rel_root == ".":
            dirs[:] = [d for d in dirs if d not in SKIPPED_TOP_DIRS]
        elif top in SKIPPED_TOP_DIRS:
            dirs[:] = []
            continue
        for name in files:
            if name.lower().endswith(IMAGE_EXTENSIONS):
                rel = name if rel_root == "." else f"{rel_root}/{name}"
                results.append(rel)
    return sorted(results)


def built_in_class(rel_path):
    return _BUILT_IN_BY_EXTENSION.get(posixpath.splitext(rel_path)[1].lower(), "vtoyiso")


def normalize_rules(raw):
    """Validate a raw menu_class value; returns a list of clean rule dicts."""
    rules = []
    if not isinstance(raw, list):
        return rules
    for item in raw:
        if not isinstance(item, dict):
            continue
        cls = item.get("class")
        if not isinstance(cls, str) or not cls:
            continue
        for match_key in ("key", "parent", "dir"):
            value = item.get(match_key)
            if isinstance(value, str) and value:
                rules.append({match_key: value, "class": cls})
                break
    return rules


def rule_matches(rule, rel_path):
    if "key" in rule:
        return rule["key"] in posixpath.basename(rel_path)
    if "parent" in rule:
        parent = rule["parent"].rstrip("/")
        return posixpath.dirname("/" + rel_path) == parent
    if "dir" in rule:
        directory = "/" + rel_path
        dir_rule = "/" + rule["dir"].strip("/")
        return directory == dir_rule or directory.startswith(dir_rule + "/")
    return False


def effective_class(rel_path, rules):
    for rule in rules:
        if rule_matches(rule, rel_path):
            return rule["class"]
    return built_in_class(rel_path)


def suggest_class(rel_path):
    name = posixpath.basename(rel_path).lower()
    for pattern, cls in SUGGEST_PATTERNS:
        if pattern in name:
            return cls
    return None


def build_rule(rel_path, cls):
    """Build a key-rule for one file.

    Ventoy matches key as a substring of the file name and REQUIRES the
    key to be strictly shorter than it (ventoy_plugin.c: patlen < namelen),
    so a key equal to the full file name never matches. Stripping the
    extension guarantees a strictly-shorter key for any normal image name.
    """
    name = posixpath.basename(rel_path)
    key = posixpath.splitext(name)[0] or name
    return {"key": key, "class": cls}


def merge_rules(existing_rules, overrides, files):
    """Combine preserved existing rules with the user's assignments.

    Generated key-rules go first (first match wins, so explicit UI
    assignments always shadow older rules for the same file). An existing
    rule survives when it matches no scanned file, or when every file it
    effectively classes (first-match) was left untouched (UNSET); a file
    the user assigned or cleared drops the rule that used to class it.
    """
    generated = []
    seen = set()
    for path in files:
        override = overrides.get(path, UNSET)
        if override is UNSET or override == "":
            continue
        rule = build_rule(path, override)
        marker = (rule["key"], rule["class"])
        if marker not in seen:
            seen.add(marker)
            generated.append(rule)

    effective_source = {}
    for path in files:
        for index, rule in enumerate(existing_rules):
            if rule_matches(rule, path):
                effective_source[path] = index
                break

    preserved = []
    for index, rule in enumerate(existing_rules):
        files_it_classes = [p for p in files if effective_source.get(p) == index]
        if not files_it_classes:
            preserved.append(rule)
            continue
        if all(overrides.get(p, UNSET) is UNSET for p in files_it_classes):
            preserved.append(rule)

    final = list(generated)
    for rule in preserved:
        marker = tuple(sorted(rule.items()))
        if marker not in seen:
            seen.add(marker)
            final.append(rule)
    return final


def read_menu_class(config):
    """Return (mode, rules): mode is "array", "absent" or "multi" (a
    per-BIOS/UEFI dict we deliberately never touch)."""
    raw = config.get("menu_class")
    if raw is None:
        return "absent", []
    if isinstance(raw, list):
        return "array", normalize_rules(raw)
    if isinstance(raw, dict):
        return "multi", []
    return "absent", []


def write_menu_class(config, rules):
    config["menu_class"] = list(rules)
    return config

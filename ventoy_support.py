from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

try:
    import win32api  # type: ignore
    import win32file  # type: ignore
except Exception:  # pragma: no cover - optional on non-Windows systems
    win32api = None
    win32file = None


THEMES_DIR_NAME = "ventoy/theme"
VENTOY_JSON_PATH = "ventoy/ventoy.json"

DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_CDROM = 5

WINDOWS_PSEUDO_FILESYSTEMS = {
    "autofs",
    "binfmt_misc",
    "bpf",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devfs",
    "devpts",
    "efivarfs",
    "fusectl",
    "fuse.lxcfs",
    "fuse.portal",
    "hugetlbfs",
    "mqueue",
    "nsfs",
    "proc",
    "pstore",
    "securityfs",
    "squashfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}


@dataclass(frozen=True)
class DriveInfo:
    root: str
    label: str
    size: str
    description: str

    @property
    def display(self) -> str:
        return f"{self.root} [{self.size}] {self.label or self.description}"


def get_base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> str:
    return str(get_base_dir().joinpath(*parts))


def get_drive_size(drive: str) -> str:
    try:
        total, _, _ = shutil.disk_usage(drive)
        return f"{total / (1024**3):.1f} GB"
    except Exception:
        return "Unknown"


def get_drive_label(drive: str) -> str:
    if win32api is not None and sys.platform.startswith("win"):
        try:
            return win32api.GetVolumeInformation(drive)[0] or ""
        except Exception:
            return ""
    return Path(drive.rstrip("\\/")).name


def get_drive_description(drive: str) -> str:
    if win32file is not None and sys.platform.startswith("win"):
        try:
            drive_type = win32file.GetDriveType(drive)
            if drive_type == DRIVE_REMOVABLE:
                return "Removable Disk"
            if drive_type == DRIVE_FIXED:
                return "Local Disk"
            if drive_type == DRIVE_CDROM:
                return "CD-ROM"
        except Exception:
            pass
    if drive.startswith("/Volumes/") or drive.startswith("/media/") or drive.startswith("/run/media/"):
        return "Removable Disk"
    return "Drive"


def _looks_like_real_mount(part) -> bool:
    mountpoint = part.mountpoint or ""
    if not mountpoint:
        return False
    if not os.path.exists(mountpoint):
        return False
    if sys.platform.startswith("win"):
        if part.fstype and part.fstype.lower() in WINDOWS_PSEUDO_FILESYSTEMS:
            return False
        return True
    return mountpoint.startswith(("/Volumes/", "/media/", "/mnt/", "/run/media/"))


def list_available_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []

    try:
        for part in psutil.disk_partitions(all=False):
            if not _looks_like_real_mount(part):
                continue

            root = part.device if sys.platform.startswith("win") else part.mountpoint
            if not root:
                continue

            if sys.platform.startswith("win") and not root.endswith("\\"):
                root += "\\"

            label = get_drive_label(root)
            description = get_drive_description(root)
            size = get_drive_size(root)
            drives.append(DriveInfo(root=root, label=label, size=size, description=description))
    except Exception:
        return []

    drives.sort(key=lambda item: item.display.lower())
    return drives


def list_drives_display() -> list[str]:
    return [drive.display for drive in list_available_drives()]


def extract_drive_root(display_string: str) -> str:
    if not display_string:
        return ""

    marker = " ["
    if marker in display_string:
        return display_string.split(marker, 1)[0].rstrip()

    return display_string.strip()

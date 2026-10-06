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

# The small FAT partition Ventoy creates next to the data partition.
VENTOY_BOOT_PARTITION_LABEL = "VTOYEFI"

# Minimum size (bytes) a plausible Ventoy data partition can have. The
# VTOYEFI boot partition is 32 MiB by default, so anything below this is
# treated as a boot partition even when the label lookup fails. Kept small
# so tiny (but real) USB sticks are not hidden.
MIN_VENTOY_DATA_SIZE = 256 * 1024**2

PSEUDO_FILESYSTEMS = {
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

# Standard locations where desktop environments auto-mount removable media.
STANDARD_REMOVABLE_MOUNT_PREFIXES = ("/Volumes/", "/media/", "/mnt/", "/run/media/")


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
    if drive.startswith(("/Volumes/", "/media/", "/run/media/")):
        return "Removable Disk"
    return "Drive"


def _system_drive_root() -> str:
    system_drive = os.environ.get("SystemDrive", "C:")
    if not system_drive.endswith("\\"):
        system_drive += "\\"
    return system_drive


def _windows_drive_type(drive: str, part=None) -> int | None:
    if win32file is not None:
        try:
            return win32file.GetDriveType(drive)
        except Exception:
            pass
    # Fallback when pywin32 is unavailable: psutil reports the drive type
    # in partition opts (e.g. "rw,fixed", "rw,removable").
    opts = (getattr(part, "opts", "") or "").lower()
    if "removable" in opts:
        return DRIVE_REMOVABLE
    if "cdrom" in opts:
        return DRIVE_CDROM
    if "fixed" in opts:
        return DRIVE_FIXED
    return None


def _linux_base_device(device: str) -> str:
    """Return the parent block device name for a partition device.

    /dev/sdb1 -> sdb, /dev/nvme0n1p1 -> nvme0n1, /dev/mmcblk0p1 -> mmcblk0
    """
    dev = os.path.basename(device)
    for prefix in ("nvme", "mmcblk"):
        if dev.startswith(prefix):
            head, _, tail = dev.rpartition("p")
            if tail.isdigit() and head:
                return head
            return dev
    return dev.rstrip("0123456789")


def _linux_device_is_removable(device: str) -> bool:
    if not device.startswith("/dev/"):
        return False
    base = _linux_base_device(device)
    if not base or base.startswith("loop") or base.startswith("ram"):
        return False
    removable_file = Path("/sys/block") / base / "removable"
    try:
        return removable_file.read_text().strip() == "1"
    except Exception:
        return False


def _is_ventoy_boot_partition(root: str, label: str) -> bool:
    if label.upper() == VENTOY_BOOT_PARTITION_LABEL:
        return True
    if Path(root.rstrip("\\/")).name.upper() == VENTOY_BOOT_PARTITION_LABEL:
        return True
    try:
        total, _, _ = shutil.disk_usage(root)
        if 0 < total < MIN_VENTOY_DATA_SIZE:
            return True
    except Exception:
        pass
    return False


def _looks_like_real_mount(part) -> bool:
    mountpoint = part.mountpoint or ""
    device = part.device or ""
    if not mountpoint or not os.path.exists(mountpoint):
        return False
    # Skip hidden mounts such as /Volumes/.timemachine on macOS.
    if Path(mountpoint).name.startswith("."):
        return False
    if part.fstype and part.fstype.lower() in PSEUDO_FILESYSTEMS:
        return False

    if sys.platform.startswith("win"):
        return True

    # Standard auto-mount locations are always accepted.
    if mountpoint.startswith(STANDARD_REMOVABLE_MOUNT_PREFIXES):
        return True

    if sys.platform.startswith("linux"):
        # Drives mounted at custom locations are still shown when the kernel
        # reports the underlying block device as removable.
        return _linux_device_is_removable(device)

    return False


def list_available_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []
    system_drive = _system_drive_root() if sys.platform.startswith("win") else ""

    try:
        for part in psutil.disk_partitions(all=False):
            if not _looks_like_real_mount(part):
                continue

            root = part.device if sys.platform.startswith("win") else part.mountpoint
            if not root:
                continue

            if sys.platform.startswith("win"):
                if not root.endswith("\\"):
                    root += "\\"
                drive_type = _windows_drive_type(root, part)
                # Show removable drives plus fixed drives, but never the
                # Windows system drive. Removable-only would hide Ventoy
                # sticks whose firmware reports them as fixed disks.
                if drive_type == DRIVE_FIXED and root == system_drive:
                    continue
                if drive_type not in (None, DRIVE_REMOVABLE, DRIVE_FIXED):
                    continue

            label = get_drive_label(root)
            if _is_ventoy_boot_partition(root, label):
                continue

            size = get_drive_size(root)
            description = get_drive_description(root)
            drives.append(DriveInfo(root=root, label=label, size=size, description=description))
    except Exception:
        return []

    drives.sort(key=lambda item: item.display.lower())
    return drives


def list_drives_display() -> list[str]:
    return [drive.display for drive in list_available_drives()]


def extract_drive_root(display_string: str) -> str:
    """Best-effort extraction of a drive root from its display string.

    Callers should prefer an explicit display -> root mapping built from
    list_available_drives(); labels containing " [" make string parsing
    ambiguous.
    """
    if not display_string:
        return ""

    marker = " ["
    if marker in display_string:
        return display_string.split(marker, 1)[0].rstrip()

    return display_string.strip()

# Boot a physical USB drive in QEMU to test Ventoy themes live.
# The drive is opened read-only (snapshot=on): guest writes go to a
# temporary overlay and the real stick cannot be modified.
#
# Usage (from tools\ or via qemu-usb.cmd):
#   .\qemu-usb.ps1                # auto-detect the Ventoy USB stick
#   .\qemu-usb.ps1 -Disk 2        # boot a specific physical disk number
#   .\qemu-usb.ps1 -Uefi          # boot through UEFI (OVMF) instead of BIOS
#   .\qemu-usb.ps1 -List          # only list USB disks and exit
param(
    [int]$Disk = -1,
    [switch]$Uefi,
    [int]$MemMB = 1024,
    [switch]$List
)
$ErrorActionPreference = "Stop"

$qemu = Join-Path $env:ProgramFiles "qemu\qemu-system-x86_64.exe"
if (-not (Test-Path $qemu)) {
    $cmd = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
    if ($cmd) { $qemu = $cmd.Source }
}
if (-not (Test-Path $qemu)) {
    Write-Error "QEMU not found. Install it with: winget install SoftwareFreedomConservancy.QEMU"
    exit 1
}
$share = Join-Path (Split-Path $qemu) "share"

$usbDisks = @(Get-Disk | Where-Object BusType -eq "USB")
$ventoyDisks = @($usbDisks | Where-Object {
    (Get-Partition -DiskNumber $_.Number -ErrorAction SilentlyContinue |
     Get-Volume -ErrorAction SilentlyContinue).FileSystemLabel -match "^(Ventoy|VTOYEFI)$"
})

if ($List) {
    $usbDisks | Select-Object Number, FriendlyName,
        @{n = "SizeGB"; e = { [math]::Round($_.Size / 1GB, 1) }},
        @{n = "Ventoy"; e = { $ventoyDisks.Number -contains $_.Number }} |
        Format-Table | Out-String | Write-Host
    exit 0
}

if ($Disk -lt 0) {
    $pick = if ($ventoyDisks.Count -eq 1) { $ventoyDisks } else { $usbDisks }
    if ($pick.Count -eq 1) {
        $Disk = $pick[0].Number
    } else {
        $usbDisks | Select-Object Number, FriendlyName,
            @{n = "SizeGB"; e = { [math]::Round($_.Size / 1GB, 1) }} |
            Format-Table | Out-String | Write-Host
        $Disk = Read-Host "Enter the PhysicalDrive number to boot"
    }
}

# Opening a raw physical drive requires an elevated process.
$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $PSCommandPath, "-Disk", $Disk, "-MemMB", $MemMB)
    if ($Uefi) { $argList += "-Uefi" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

Write-Host "Booting \\.\PhysicalDrive$Disk in QEMU (snapshot mode: the stick cannot be modified)."
Write-Host "Close the QEMU window to exit."
$args = @("-m", $MemMB, "-drive", "file=\\.\PhysicalDrive$Disk,format=raw,snapshot=on")
if ($Uefi) {
    $args += @("-bios", (Join-Path $share "edk2-x86_64-code.fd"))
} else {
    $args += @("-boot", "c")
}
& $qemu @args

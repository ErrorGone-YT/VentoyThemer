@echo off
rem Double-clickable launcher: boot a USB stick in QEMU to test Ventoy themes.
rem The stick opens read-only (snapshot mode). See qemu-usb.ps1 for options.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qemu-usb.ps1" %*
pause

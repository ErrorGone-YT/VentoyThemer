<div align="center">

<img src="VentoyThemer/Logo.png" width="96" alt="VentoyThemer Logo">

# VentoyThemer

**A cross-platform GUI for installing and managing Ventoy USB boot themes**

[![Release](https://img.shields.io/github/v/release/ErrorGone-YT/VentoyThemer?logo=github)](https://github.com/ErrorGone-YT/VentoyThemer/releases)
[![License](https://img.shields.io/github/license/ErrorGone-YT/VentoyThemer)](LICENSE.txt)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#requirements-for-running-from-source)
[![Languages](https://img.shields.io/badge/interface-58%20languages-green)](#translations)

[Download](https://github.com/ErrorGone-YT/VentoyThemer/releases) · [How to Use](#how-to-use) · [Translations](#translations) · [Donate](https://errorgone-yt.github.io/Donat)

</div>

---

## About

**VentoyThemer** is a graphical application for Windows, Linux, and macOS designed to simplify the process of installing and managing themes for Ventoy. It allows you to easily add themes from various archive formats (ZIP, TAR.GZ, 7z, RAR, and others) or theme folders, manage theme settings (default theme, resolution), assign boot-menu icons to your ISO files, and remove installed themes from your Ventoy drive.

Version 1.1.0 introduces a redesigned **web-based interface** (HTML/CSS/JS in a native window via pywebview) that looks and behaves identically on every operating system, with a **live theme preview**: pick a theme and instantly see its background, menu geometry, colors and per-file boot icons rendered before you apply anything.

The app is written in Python; the interface is HTML/CSS/JS rendered by the OS-native web engine (WebView2 on Windows, WebKitGTK on Linux, WKWebView on macOS). The classic Tkinter interface remains available as a fallback via `python VentoyThemer.py`.

## Features

### Themes

* Automatic detection of connected Ventoy drives.
* Installation of themes from various archive formats (.zip, .tar.gz, .7z, .rar, etc.) or directly from a theme folder (containing `theme.txt`).
* Support for Drag & Drop of theme archives or folders.
* GUI-based configuration of the default theme and screen resolution.
* Removal of individual installed themes or all installed themes at once.
* Automatic updating of `ventoy.json` after theme installation/removal and settings changes.

### Live theme preview

* Selecting an installed theme instantly renders its real `theme.txt` look: background image, menu geometry, colors and fonts — before you apply anything.
* The preview lists the actual ISO/WIM/VHD files on the drive with their boot icons and reflects every change as you edit.

### Boot-menu icons

* Assign an icon to each ISO/WIM file individually, or let Auto-Suggest fill everything in one click (Windows, Ubuntu, Arch, Debian and ~30 more distributions recognized by filename).
* Pick the icon source: any installed theme, or your own folder of icons — copied to the drive as a reusable icon pack.
* Icons are applied per theme with automatic backup and exact restore of each theme's original icons.
* Overwrite protection when installing a theme that already exists: overwrite, skip or install as a copy.

### Custom backgrounds

* Replace a theme's background with your own image: drag it into the window or pick it from disk — it is copied to `ventoy/wallpapers/` on the drive.
* Switch between the theme's original background and your wallpapers at any time; removing a wallpaper restores the original automatically.

### General

* Single-window interface (HTML/CSS/JS in a native OS window) that looks identical on Windows, Linux and macOS.
* Multilingual interface (58 languages, loaded from `languages.json`) with automatic OS locale detection and instant switching.

## Screenshots
![Install Themes](https://github.com/user-attachments/assets/e4a32045-2660-422a-86cb-1cb9ce0dbf4b)
![Themes Settings](https://github.com/user-attachments/assets/d4b7cc4b-7faa-483c-a805-ba08844eed6e)
![Remove Themes](https://github.com/user-attachments/assets/a96fe211-425f-48d8-a4fb-e1e54fbf1c5e)
![Application Settings](https://github.com/user-attachments/assets/b528a3e0-e35f-4432-8bae-e9348d418346)
## Requirements (for running from source)

* Python 3.8 or higher (3.12+ recommended).
* Required Python libraries (installed with `pip install -r requirements.txt`):
    * `pywebview` — renders the interface (WebView2 on Windows is bundled with the OS; on Linux install `libwebkit2gtk-4.1-0` and `gir1.2-webkit2-4.1` via apt; on macOS WKWebView is built-in)
    * `tkinter` + `tkinterdnd2` (only for the classic Tkinter fallback UI)
    * `psutil`
    * `py7zr` (for .7z archives)
    * `rarfile` (for .rar archives, requires the `unrar` utility installed and available in your system's PATH)
    * `zstandard` (for .zst archives)
    * `lz4` (for .lz4 archives)

Note: For .rar archives, you might also need to install the `unrar` command-line utility on your operating system and ensure its directory is added to your system's PATH variable.

Note for Linux: the application runs under both X11 and Wayland (through XWayland). Drag & Drop relies on `tkinterdnd2` and may be unreliable under pure Wayland compositors; the Browse button always works.

## Installation and Usage

### Running from Source

1.  Clone the repository or download the ZIP archive of the source code.
2.  Navigate to the project folder in your terminal.
3.  Install the required libraries (see Requirements section).
4.  Run the application:
    ```bash
    python main_web.py
    ```
    The classic Tkinter interface is still available via `python VentoyThemer.py` if you prefer it.

### Using a Ready-Made Executable

Go to the project's [Releases page](https://github.com/ErrorGone-YT/VentoyThemer/releases) and download the release that matches your operating system. Extract the archive and run the bundled application. No Python or library installation is required when using the packaged build.

## How to Use

1.  Connect your Ventoy USB drive to your computer.
2.  Select the Ventoy drive from the "Device" dropdown list. The application will automatically load any existing themes and settings from `ventoy.json`.
3.  **To Install a Theme:**
    * Click **Browse** and select one or more theme archives (.zip, .tar.gz, .7z, .rar, etc.) or theme folders, or simply drag & drop them into the window.
    * Click **Install**. The application extracts the themes to the drive and updates `ventoy.json`.
    * If a theme already exists, you will be asked to overwrite it, skip it, or install it as a copy.
4.  **To Preview and Configure:**
    * Click a theme in the **Installed themes** list — the live preview instantly shows its background, menu colors and boot entries with icons.
    * Use the **Default theme** and **Resolution** dropdowns to configure the boot menu; changes are applied immediately.
5.  **To Customize Boot Icons:**
    * Open the **Menu icons** panel. Every image file on the drive is listed with its current boot icon.
    * Pick an **Icon source** (any installed theme, or your own icon folder), then click **Auto-Suggest** to assign icons by filename — or assign them manually and click **Apply Menu Classes**.
    * The preview updates as you edit.
6.  **To Use Your Own Background:**
    * Drag an image into the window or use **Add** — it is copied to `ventoy/wallpapers/` on the drive.
    * Select it in the **Background** dropdown to replace the theme's background; select **Theme background** to restore the original.
7.  **To Remove a Theme:**
    * Click the **✕** button next to the theme in the **Installed themes** list and confirm.

## Building from Source (for Developers)

The application uses PyInstaller to create standalone executables.

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Ensure you have all the necessary libraries installed to run the application from source (see Requirements section).
3.  Navigate to the root project folder in your terminal.
4.  Run the build script:
    ```bash
    python build.py
    ```
    This will create a `dist/VentoyThemer-[Version]/` folder containing the packaged application and all required files.

## Translations

The application supports a multilingual interface. All translations are stored in the `VentoyThemer/languages.json` file. If you would like to add a new language or improve an existing translation, you can edit this file and submit a Pull Request.

The `languages.json` file format is a JSON array, where each element in the array is a JSON object representing a language. Each object must contain a `"name"` key with the language name (e.g., "English", "Русский") and other key-value pairs for translating interface strings.

## Contributing

Contributions are welcome! You can:

* Report bugs (Issues).
* Suggest new features (Issues).
* Propose code changes (Pull Requests).
* Add or improve translations.

Please open an Issue or Pull Request on GitHub for any suggestions or changes.

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE.txt](LICENSE.txt) file for details.

## Useful Links

* [Author's Donation Page](https://errorgone-yt.github.io/Donat)
* [Download New Themes for Ventoy](https://www.gnome-look.org/browse?cat=109&ord=latest)
* [Project Page on GitHub](https://github.com/ErrorGone-YT/VentoyThemer) 

CREATED BY: Error Gone (ErrorGone-YT)

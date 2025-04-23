# VentoyThemer

![VentoyThemer Logo](VentoyThemer/Logo.ico)

VERSION: [1.0.1]

## About

**VentoyThemer** is a graphical application for Windows designed to simplify the process of installing and managing themes for Ventoy. It allows you to easily add themes from various archive formats (ZIP, TAR.GZ, 7z, RAR, and others) or theme folders, manage theme settings (default theme, resolution), and remove installed themes from your Ventoy USB drive.

The application is written in Python using the Tkinter library and the TkinterDnD2 extension for Drag & Drop functionality.

## Features

* Automatic detection of connected Ventoy drives.
* Installation of themes from various archive formats (.zip, .tar.gz, .7z, .rar, etc.) or directly from a theme folder (containing `theme.txt`).
* Support for Drag & Drop of theme archives or folders.
* GUI-based configuration of the default theme and screen resolution.
* Removal of individual installed themes.
* Removal of all installed themes.
* Automatic updating of `ventoy.json` after theme installation/removal and settings changes.
* Multilingual interface (translations loaded from `languages.json`).

## Screenshots
![Install Themes](https://github.com/user-attachments/assets/e4a32045-2660-422a-86cb-1cb9ce0dbf4b)
![Themes Settings](https://github.com/user-attachments/assets/d4b7cc4b-7faa-483c-a805-ba08844eed6e)
![Remove Themes](https://github.com/user-attachments/assets/a96fe211-425f-48d8-a4fb-e1e54fbf1c5e)
![Application Settings](https://github.com/user-attachments/assets/b528a3e0-e35f-4432-8bae-e9348d418346)
## Requirements (for running from source)

* Python 3.6 or higher.
* Required Python libraries:
    * `tkinter` (usually included with Python standard installation)
    * `tkinterdnd2`
    * `psutil`
    * `py7zr` (for .7z archives)
    * `rarfile` (for .rar archives, requires the `unrar` utility installed and available in your system's PATH)
    * `zstandard` (for .zst archives)
    * `lz4` (for .lz4 archives)
    * `pywin32` (for `win32api` and `win32file` modules, used for drive interaction on Windows)

You can install the required libraries using pip:

```bash
pip install tkinterdnd2 psutil py7zr rarfile zstandard lz4 pywin32
````
Note: For .rar archives, you might also need to install the `unrar` command-line utility on your operating system and ensure its directory is added to your system's PATH variable.

## Installation and Usage

### Running from Source

1.  Clone the repository or download the ZIP archive of the source code.
2.  Navigate to the project folder in your terminal.
3.  Install the required libraries (see Requirements section).
4.  Run the application:
    ```bash
    python VentoyThemer-1.1.44.py # Or the name of your main script file
    ```

### Using a Ready-Made Executable (EXE)

Go to the project's [Releases page](https://github.com/ErrorGone-YT/VentoyThemer/releases) and download the latest `.zip` archive containing the executable. Extract the archive and run the `.exe` file inside the extracted folder. No Python or library installation is required when using the executable build.

## How to Use

1.  Connect your Ventoy USB drive to your computer.
2.  Select the Ventoy drive from the "Device" dropdown list. The application will automatically load any existing themes and settings from `ventoy.json`.
3.  **To Install Themes:**
    * Go to the "Install Themes" tab.
    * Click the "Browse" button and select one or more theme archives (.zip, .tar.gz, .7z, .rar, etc.) or theme folders (containing `theme.txt`).
    * Alternatively, simply Drag & Drop the theme archives or folders directly into the listbox area.
    * Selected items will appear in the list.
    * Click the "Apply Themes" button. The application will extract/copy the themes to the Ventoy drive and update the `ventoy.json` configuration.
4.  **To Configure Themes:**
    * Go to the "Themes Settings" tab.
    * Select the desired default theme from the "Select Default Theme" dropdown list.
    * Choose the standard resolution from the "Choose Standard Resolution" dropdown list.
    * Click the "Apply settings" button. The application will update the settings in `ventoy.json`.
5.  **To Remove Themes:**
    * Go to the "Remove Themes" tab.
    * Select the theme you want to delete from the "Choose Theme to Delete" dropdown list.
    * Click the "Remove Selected Theme" button.
    * To delete **all** installed themes, click the "Remove ALL THEMES" button.
    * Confirm the action in the dialog window.

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
    This will create a `dist/VentoyThemer-[Version]/` folder containing the executable and all required files.

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


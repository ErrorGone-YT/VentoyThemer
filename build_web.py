"""Build the web-UI entry (main_web.py) into a standalone Windows app.

The classic Tkinter build remains in build.py. This one bundles the
pywebview runtime (hooks ship with pywebview) plus the webui/ assets.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import ventoy_version as version_service

ROOT_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = ROOT_DIR / 'main_web.py'
VERSION_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'version'
BASE_NAME = 'VentoyThemer'
ICON_PATH_SOURCE = ROOT_DIR / 'VentoyThemer' / 'Logo.ico'
LANGUAGES_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'languages.json'
LICENSE_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'LICENSE.txt'
WEBUI_DIR_SOURCE = ROOT_DIR / 'webui'
DATA_FILES = [
    (str(WEBUI_DIR_SOURCE), 'webui'),
    (str(LANGUAGES_FILE_SOURCE), 'VentoyThemer'),
    (str(VERSION_FILE_SOURCE), 'VentoyThemer'),
    (str(LICENSE_FILE_SOURCE), 'VentoyThemer'),
]
app_version = version_service.load_version(default="")
if not app_version:
    print(f"Error: {VERSION_FILE_SOURCE} is empty or missing.")
    sys.exit(1)
print(f"Read version: {app_version}")
executable_name = f"{BASE_NAME}-{app_version}"
print(f"Building web app with name: {executable_name}")
command = [
    sys.executable, '-m', 'PyInstaller',
    '--onedir',
    '--windowed',
    '--noconfirm',
    f'--name={executable_name}',
]
if ICON_PATH_SOURCE.exists():
    command.append(f'--icon={ICON_PATH_SOURCE}')
for source, destination_folder_name in DATA_FILES:
    data_arg = f"{source}{os.pathsep}{destination_folder_name}"
    command.extend(['--add-data', data_arg])
command.append(str(MAIN_SCRIPT))
print("Executing PyInstaller command:")
print(" \\\n  ".join(command))

try:
    subprocess.run(command, check=True, cwd=str(ROOT_DIR))
    dist_dir = ROOT_DIR / 'dist' / executable_name
    if dist_dir.exists():
        readme_source = ROOT_DIR / 'README.md'
        readme_target = dist_dir / 'README.md'
        if readme_source.exists():
            shutil.copy2(readme_source, readme_target)

        resources_source = ROOT_DIR / 'VentoyThemer'
        resources_target = dist_dir / 'VentoyThemer'
        if resources_target.exists():
            shutil.rmtree(resources_target)
        if resources_source.exists():
            shutil.copytree(resources_source, resources_target, ignore=shutil.ignore_patterns('*.py'))

    print("\nPyInstaller build finished successfully!")
    print(f"Build directory: ./dist/{executable_name}/")
    print(f"Inside: {executable_name}.exe, _internal/, webui/, VentoyThemer/")

except subprocess.CalledProcessError as e:
    print(f"\nPyInstaller build failed with error code {e.returncode}")
    print("Please check the output above for specific PyInstaller error messages.")
except Exception as e:
    print(f"\nAn unexpected error occurred during PyInstaller execution: {e}")

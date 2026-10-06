import os
import shutil
import subprocess
import sys
from pathlib import Path

import ventoy_version as version_service

ROOT_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = ROOT_DIR / 'VentoyThemer.py'
VERSION_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'version'
BASE_NAME = 'VentoyThemer'
ICON_PATH_SOURCE = ROOT_DIR / 'VentoyThemer' / 'Logo.ico'
LICENSE_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'LICENSE.txt'
LANGUAGES_FILE_SOURCE = ROOT_DIR / 'VentoyThemer' / 'languages.json'
DATA_FILES = [
    (str(ROOT_DIR / 'VentoyThemer' / 'languages.json'), 'VentoyThemer'),
    (str(ROOT_DIR / 'VentoyThemer' / 'Logo.ico'), 'VentoyThemer'),
    (str(ROOT_DIR / 'VentoyThemer' / 'Logo.png'), 'VentoyThemer'),
    (str(ROOT_DIR / 'VentoyThemer' / 'LICENSE.txt'), 'VentoyThemer'),
    (str(ROOT_DIR / 'VentoyThemer' / 'version'), 'VentoyThemer'),
    (str(ROOT_DIR / 'vendor' / 'sv_ttk'), 'vendor/sv_ttk'),
]
app_version = version_service.load_version(default="")
if not app_version:
    print(f"Error: {VERSION_FILE_SOURCE} is empty or missing.")
    sys.exit(1)
if app_version.startswith("Error loading version:"):
    print(app_version)
    sys.exit(1)
print(f"Read version: {app_version}")
executable_name = f"{BASE_NAME}-{app_version}"
print(f"Building app with name: {executable_name}")
command = [
    sys.executable, '-m', 'PyInstaller',
    '--onedir',
    '--windowed',
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
            shutil.copytree(resources_source, resources_target)

    print("\nPyInstaller build finished successfully!")
    print(f"Build directory should be in ./dist folder: ./dist/{executable_name}/")
    print(f"Inside './dist/{executable_name}/' you should find the packaged app binary:")
    if sys.platform.startswith('win'):
        print(f" - {executable_name}.exe")
    else:
        print(f" - {executable_name}")
    print(f" - _internal/")
    print(f" - VentoyThemer/")
    print(f"    - Logo.ico")
    print(f"    - Logo.png")
    print(f"    - languages.json")
    print(f"    - LICENSE.txt")
    print(f"    - version")

except subprocess.CalledProcessError as e:
    print(f"\nPyInstaller build failed with error code {e.returncode}")
    print("Please check the output above for specific PyInstaller error messages from PyInstaller.")
except Exception as e:
    print(f"\nAn unexpected error occurred during PyInstaller execution: {e}")

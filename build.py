import os
import subprocess
import sys
MAIN_SCRIPT = 'VentoyThemer-1.0.1.py'
VERSION_FILE_SOURCE = os.path.join('VentoyThemer','version')
BASE_NAME = 'VentoyThemer'
ICON_PATH_SOURCE = os.path.join('VentoyThemer', 'Logo.ico')
LICENSE_FILE_SOURCE = os.path.join('VentoyThemer', 'LICENSE.txt')
LANGUAGES_FILE_SOURCE = os.path.join('VentoyThemer', 'languages.json')
DATA_FILES = [
    (os.path.join('VentoyThemer', 'languages.json'), 'VentoyThemer'),
    (os.path.join('VentoyThemer', 'Logo.ico'), 'VentoyThemer'),
    (os.path.join('VentoyThemer', 'LICENSE.txt'), 'VentoyThemer'),
    (os.path.join('VentoyThemer', 'version'), 'VentoyThemer'),
]
try:
    with open(VERSION_FILE_SOURCE, 'r', encoding='utf-8') as f:
        app_version = f.read().strip()
    if not app_version:
        print(f"Error: {VERSION_FILE_SOURCE} is empty.")
        sys.exit(1)
    print(f"Read version: {app_version}")
except FileNotFoundError:
    print(f"Error: {VERSION_FILE_SOURCE} not found. Make sure it exists in the '{os.path.dirname(VERSION_FILE_SOURCE)}' subdirectory.")
    sys.exit(1)
except Exception as e:
    print(f"Error reading {VERSION_FILE_SOURCE}: {e}")
    sys.exit(1)
executable_name = f"{BASE_NAME}-{app_version}"
print(f"Building executable with name: {executable_name}")
command = [
    sys.executable, '-m', 'PyInstaller',
    '--onedir',
    '--windowed',
    f'--name={executable_name}',
    f'--icon={ICON_PATH_SOURCE}',

]
for source, destination_folder_name in DATA_FILES:
    data_arg = f"{source}{os.pathsep}{destination_folder_name}"
    command.extend(['--add-data', data_arg])
command.append(MAIN_SCRIPT)
print("Executing PyInstaller command:")
print(" \\\n  ".join(command))

try:
    subprocess.run(command, check=True, cwd=os.path.dirname(os.path.abspath(__file__)))
    print("\nPyInstaller build finished successfully!")
    print(f"Build directory should be in ./dist folder: ./dist/{executable_name}/")
    print(f"Inside './dist/{executable_name}/' you should find:")
    print(f" - {executable_name}.exe")
    print(f" - _internal/")
    print(f" - VentoyThemer/")
    print(f"    - Logo.ico")
    print(f"    - languages.json")
    print(f"    - LICENSE.txt")
    print(f"    - version")

except subprocess.CalledProcessError as e:
    print(f"\nPyInstaller build failed with error code {e.returncode}")
    print("Please check the output above for specific PyInstaller error messages from PyInstaller.")
except Exception as e:
    print(f"\nAn unexpected error occurred during PyInstaller execution: {e}")
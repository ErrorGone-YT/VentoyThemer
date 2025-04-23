#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) [2025] [Error Gone]
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import Menu
from tkinter import filedialog, messagebox, ttk
import zipfile
import os
import json
import tarfile
import psutil
import tkinter.font as tkFont
from tkinterdnd2 import TkinterDnD, DND_FILES
import win32api
import win32file
import shutil
import webbrowser
import threading
import traceback
import queue
import sys

THEMES_DIR_NAME = "ventoy/theme"
VENTOY_JSON_PATH = "ventoy/ventoy.json"
OUTER_PADDING = 10
SECTION_SPACING = 5
TITLE_SPACING = 5
INNER_PADDING = 5
WIDGET_SPACING = 5
BUTTON_GROUP_SPACING = 5
LARGE_SECTION_SPACING = 40
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3

def get_drive_label(drive):
    try:
        return win32api.GetVolumeInformation(drive)[0]
    except Exception:
        return ""

def get_drive_size(drive):
    try:
        total, _, _ = shutil.disk_usage(drive)
        return f"{total / (1024**3):.1f} GB"
    except Exception:
        return "Unknown"

def get_drive_description(drive):
    try:
        name = win32file.GetDriveType(drive)
        if name == DRIVE_REMOVABLE:
            return "Removable Disk"
        elif name == DRIVE_FIXED:
            return "Local Disk"
        elif name == 5:
            return "CD-ROM"
        else:
            return "Drive"
    except Exception:
        return "Drive"

def list_drives_display():
    drives = []
    try:
        for part in psutil.disk_partitions(all=False):
            drive = part.device
            if not drive.endswith("\\"):
                drive += "\\"

            try:
                drive_type = win32file.GetDriveType(drive)
            except Exception:
                drive_type = 0

            if drive_type in [DRIVE_REMOVABLE, DRIVE_FIXED] and os.path.exists(drive):
                size = get_drive_size(drive)
                label = get_drive_label(drive)

                if not label:
                    label = get_drive_description(drive)

                display = f"{drive} [{size}] {label}"
                drives.append(display)

    except Exception as e:
        print(f"Error listing drives: {e}")

    drives.sort()
    return drives


def extract_drive_letter(display_string):
    if not display_string or ' ' not in display_string:
        return ""
    return display_string.split()[0]

class VentoyThemer:
    def __init__(self, root):
        self.root = root
        base_dir = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
        translation_file_path = os.path.join(base_dir, "VentoyThemer", "languages.json")

        self.all_translations = []
        self._messages = {}

        try:
            if os.path.exists(translation_file_path):
                with open(translation_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if isinstance(loaded_data, list) and loaded_data:
                    self.all_translations = loaded_data
                    if self.all_translations and self.all_translations[0] and isinstance(self.all_translations[0], dict):
                         self._messages = self.all_translations[0]
                         print("Translations loaded successfully. Using the first language as default.")
                    else:
                         print(f"Warning: First language in '{translation_file_path}' has unexpected format. Using fallback keys.")
                         self._messages = {}
                else:
                    print(f"Warning: Translation file '{translation_file_path}' is empty or has unexpected format (not a list). Using fallback keys.")
                    self.all_translations = []
                    self._messages = {}

            else:
                print(f"Warning: Translation file not found at '{translation_file_path}'. Using fallback keys.")
                self.all_translations = []
                self._messages = {}

        except json.JSONDecodeError as e:
             print(f"Error decoding translation JSON from '{translation_file_path}': {e}. Using fallback keys.")
             self.all_translations = []
             self._messages = {}
        except Exception as e:
            print(f"Error loading translation file '{translation_file_path}': {e}. Using fallback keys.")
            self.all_translations = []
            self._messages = {}
        self.root.geometry("440x385")
        root.resizable(False, False)
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(base_dir, 'VentoyThemer', 'Logo.ico')
            else:
                icon_path = "Logo.ico"

            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
            else:
                print(f"Warning: Icon file not found at {icon_path}")

        except Exception as e:
            print(f"Error setting window icon: {e}")
            
        self.default_font = ("Courier New", 10)
        self.app_font = tkFont.Font(family=self.default_font[0], size=self.default_font[1])
        self.link_font = tkFont.Font(family=self.default_font[0], size=self.default_font[1], underline=True)
        self.theme_sources_paths = []
        self.theme_display_names_from_json = []

        self.drive_var = tk.StringVar()
        self.default_theme_var = tk.StringVar()
        self.resolution_var = tk.StringVar()
        self.language_var = tk.StringVar()
        
        self.app_version = "Unknown" 
        self._load_version() 

        self.style = ttk.Style()
        self.status_bar_install = tk.StringVar()
        self.progress_value_install = tk.DoubleVar(value=0)

        self.status_bar_settings = tk.StringVar()
        self.progress_value_settings = tk.DoubleVar(value=0)

        self.status_bar_remove = tk.StringVar()
        self.progress_value_remove = tk.DoubleVar(value=0)
        self.worker_thread = None
        self.current_drive = ""
        self.drive_combos = []
        self.language_combo = None

        self.translatable_widgets = []
        self.define_styles()
        self.create_widgets()
        if self._messages and 'name' in self._messages:
             self.language_var.set(self._messages['name'])
        elif self.all_translations and self.all_translations[0] and isinstance(self.all_translations[0], dict) and 'name' in self.all_translations[0]:
             self.language_var.set(self.all_translations[0]['name'])
        elif self.all_translations and self.all_translations[0] and isinstance(self.all_translations[0], dict):
             self.language_var.set(f"Unnamed {0}")
        else:
             self.language_var.set("Default")
        self.update_gui_language()
        self.update_usb_drives()

    def update_gui_language(self):
        """Updates translatable GUI elements with the currently selected language."""
        self.root.title(self._("window_title", "VentoyThemer"))
        current_tabs = self.notebook.tabs()
        if len(current_tabs) > 0:
            self.notebook.tab(current_tabs[0], text=self._("install_tab_title", "Install Themes"))
        if len(current_tabs) > 1:
            self.notebook.tab(current_tabs[1], text=self._("settings_tab_title", "Themes Settings"))
        if len(current_tabs) > 2:
            self.notebook.tab(current_tabs[2], text=self._("remove_tab_title", "Remove Themes"))
        if len(current_tabs) > 3:
             self.notebook.tab(current_tabs[3], text=self._("language_tab_title", "Language"))

        for widget, key in self.translatable_widgets:
            if widget and widget.winfo_exists():
                try:
                    if key == "app_version_label":
                        translated_format_string = self._(key, key) 
                        translated_text = translated_format_string.format(self.app_version) # 
                    else:
                         translated_text = self._(key, key)

                    widget.config(text=translated_text)
                except Exception as e:
                     print(f"Warning: Could not update text for widget with key '{key}': {e}")

        self.status_bar_install.set(self._("status_ready", "Status - READY"))
        self.status_bar_settings.set(self._("status_ready", "Status - READY"))
        self.status_bar_remove.set(self._("status_ready", "Status - READY"))


    def _load_version(self):
        """Loads the application version from the 'version' file."""
        base_dir = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
        version_file_path = os.path.join(base_dir, "VentoyThemer", "version")

        try:
            if os.path.exists(version_file_path):
                with open(version_file_path, 'r', encoding='utf-8') as f:
                    self.app_version = f.read().strip()
                    if not self.app_version: 
                         self.app_version = "Unknown (Empty File)"
            else:
                self.app_version = "Unknown (File not found)"
                print(f"Warning: Version file not found at {version_file_path}")
        except Exception as e:
             self.app_version = f"Error loading version: {e}"
             print(f"Error reading version file {version_file_path}: {e}")

    def _(self, key, default=None):
        """
        Looks up a translation key in the currently active messages dictionary (_messages).
        """
        if self._messages and key in self._messages:
            return self._messages[key]
        else:
             if default is not None:
                 return default
             return key

    def _get_truncated_name(self, name, max_length=33, ellipsis="..."):
        if len(name) > max_length:
            return name[:max_length - len(ellipsis)] + ellipsis
        return name

    def on_default_theme_selected(self, event=None):
        pass

    def _show_overwrite_dialog_threaded(self, theme_name, result_queue):
        dialog_title = self._("dialog_confirm_overwrite_title", "Confirm Overwrite")
        question = self._("dialog_confirm_overwrite_message", "Theme '{theme_name}' already exists.\\nDo you want to overwrite it?\\n\\nAll previous changes will be LOST!").format(theme_name=theme_name)

        overwrite_confirm = messagebox.askyesno(dialog_title, question)

        try:
            result_queue.put(overwrite_confirm, block=False)
        except queue.Full:
            print(f"Warning: Dialog result queue for '{theme_name}' was full.")

    def define_styles(self):
        self.root.option_add("*Font", self.default_font)
        self.root.option_add("*Listbox*Font", self.default_font)
        self.root.option_add("*TLabel*Font", self.default_font)
        self.root.option_add("*TButton*Font", self.default_font)
        self.root.option_add("*TCombobox*Font", self.default_font)
        self.root.option_add("*TCombobox*Listbox*Font", self.default_font)
        self.root.option_add("*TLabelframe*Font", self.default_font)
        self.root.option_add("*TEntry*Font", self.default_font)

        self.style.configure("TLabel", font=self.default_font)
        self.style.configure("Courier.TLabel", font=self.default_font)

        self.style.configure("TButton", font=self.default_font)
        self.style.configure("RoundedButton.TButton",
                             relief="flat",
                             background=self.root.cget("background"),
                             foreground="#000000",
                             padding=10,
                             borderwidth=0,
                             font=self.default_font,
                             takefocus=False)
        self.style.map("RoundedButton.TButton",
                       background=[('active', '#e6f2ff'), ('!active', self.root.cget("background"))],
                       foreground=[('active', '#000000')])

        self.style.configure("TCombobox", font=self.default_font)
        self.style.configure("Courier.TCombobox", font=self.default_font)

        self.style.configure("TLabelframe", font=self.default_font)
        self.style.configure("Courier.TLabelframe", font=self.default_font)

    def clear_zip_selection(self):
        self.theme_listbox.delete(0, tk.END)
        self.theme_sources_paths = []

    def add_footer_links(self):
        footer = tk.Frame(self.root)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

        link_font = tkFont.Font(family="Courier New", size=10, underline=True)

        left_frame = tk.Frame(footer)
        center_frame = tk.Frame(footer)
        right_frame = tk.Frame(footer)

        left_frame.pack(side=tk.LEFT, expand=False, anchor="w", padx=10)

        right_frame.pack(side=tk.RIGHT, expand=False, anchor="e", padx=10)

        center_frame.pack(side=tk.LEFT, expand=True, anchor="center")

        link1 = tk.Label(left_frame,
                         text=self._("donate_link_text", "Donate"),
                         fg="blue", cursor="hand2", font=link_font)
        link1.pack() 
        link1.bind("<Button-1>", lambda e: webbrowser.open("https://errorgone-yt.github.io/Donat"))
        self.translatable_widgets.append((link1, "donate_link_text"))

        link2 = tk.Label(center_frame,
                         text=self._("download_themes_link_text", "Download New Theme"),
                         fg="blue", cursor="hand2", font=link_font)
        link2.pack() 
        link2.bind("<Button-1>", lambda e: webbrowser.open("https://www.gnome-look.org/browse?cat=109&ord=latest"))
        self.translatable_widgets.append((link2, "download_themes_link_text"))

        link3 = tk.Label(right_frame,
                         text=self._("ventoy_themer_link_text", "Project Page"),
                         fg="blue", cursor="hand2", font=link_font)
        link3.pack() 
        link3.bind("<Button-1>", lambda e: webbrowser.open("https://www.ventoy.net/en/index.html"))
        self.translatable_widgets.append((link3, "ventoy_themer_link_text"))

    def reset_status(self):
        selected_tab = self.notebook.index(self.notebook.select())
        status_text = self._("status_ready", "Status - READY")

        if selected_tab == 0:
            self.status_bar_install.set(status_text)
            self.progress_value_install.set(0)
        elif selected_tab == 1:
            self.status_bar_settings.set(status_text)
            self.progress_value_settings.set(0)
        elif selected_tab == 2:
            self.status_bar_remove.set(status_text)
            self.progress_value_remove.set(0)

    def update_status_safe(self, tab_index, message, progress=None):
        def update_gui():
            if tab_index == 0:
                self.status_bar_install.set(message)
                if progress is not None:
                    self.progress_value_install.set(progress)
            elif tab_index == 1:
                self.status_bar_settings.set(message)
                if progress is not None:
                    self.progress_value_settings.set(progress)
            elif tab_index == 2:
                self.status_bar_remove.set(message)
                if progress is not None:
                    self.progress_value_remove.set(progress)

            self.root.update_idletasks()

        self.root.after(0, update_gui)

    def show_message_safe(self, type, title_key, message_key, *args, **kwargs):
        def show_gui_message():
            translated_title = self._(title_key, title_key)

            if message_key:
                 translated_message = self._(message_key, message_key)
                 try:
                      formatted_message = translated_message.format(*args, **kwargs)
                 except (IndexError, KeyError) as e:
                      print(f"Formatting error for message key '{message_key}': {e}. Using raw translation.")
                      formatted_message = translated_message
            else:
                 formatted_message = args[0] if args else "Unknown Message"
                 if (args or kwargs) and not message_key:
                     print(f"Warning: show_message_safe called without message_key but with args/kwargs. Args: {args}, kwargs: {kwargs}")

            if type == "info":
                messagebox.showinfo(translated_title, formatted_message)
            elif type == "warning":
                messagebox.showwarning(translated_title, formatted_message)
            elif type == "error":
                messagebox.showerror(translated_title, formatted_message)
            else:
                 print(f"Error: show_message_safe called with unsupported type: {type}")

        self.root.after(0, show_gui_message)

    def set_buttons_state(self, state):
        def set_state():
            for btn in [self.apply_btn_install, self.browse_btn_install, self.clear_btn_install]:
                 if btn and btn.winfo_exists():
                     btn.config(state=state)

            for btn in [self.apply_btn_settings]:
                 if btn and btn.winfo_exists():
                     btn.config(state=state)

            for btn in [self.remove_btn, self.remove_all_btn]:
                 if btn and btn.winfo_exists():
                     btn.config(state=state)

            for combo in self.drive_combos:
                 if combo and combo.winfo_exists():
                     combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

            if self.default_theme_combo and self.default_theme_combo.winfo_exists():
                 self.default_theme_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
            if self.resolution_combo and self.resolution_combo.winfo_exists():
                 self.resolution_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

            if self.remove_theme_combo and self.remove_theme_combo.winfo_exists():
                 self.remove_theme_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

            if self.theme_listbox and self.theme_listbox.winfo_exists():
                 self.theme_listbox.config(state=state)

        self.root.after(0, set_state)

    def extract_theme(self, archive_path, dest_path):
        archive_path_lower = archive_path.lower()

        if archive_path_lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".zip", os.path.basename(archive_path)))
            except zipfile.BadZipFile:
                raise Exception(self._("error_zip_bad_file", "Failed to extract .zip archive '{}': Not a valid ZIP file.").format(os.path.basename(archive_path)))
            except Exception as e:
                raise Exception(self._("error_zip_extraction_error", "Failed to extract .zip archive '{}': {}").format(os.path.basename(archive_path), e))

        elif archive_path_lower.endswith(".zipx"):
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                     zip_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".zipx", os.path.basename(archive_path)))
            except zipfile.BadZipFile as e:
                 raise Exception(self._("error_zipx_bad_file", "Failed to extract .zipx archive '{}': Unsupported compression method or not a valid ZipX file. Error: {}").format(os.path.basename(archive_path), e))
            except Exception as e:
                raise Exception(self._("error_zipx_extraction_error", "Failed to extract .zipx archive '{}': {}").format(os.path.basename(archive_path), e))


        elif archive_path_lower.endswith((".tar", ".tar.gz", ".tgz")):
            try:
                mode = 'r:gz' if archive_path_lower.endswith((".tar.gz", ".tgz")) else 'r'
                with tarfile.open(archive_path, mode) as tar_ref:
                    tar_ref.extractall(dest_path)
                archive_type = ".tar.gz/.tgz" if mode == 'r:gz' else ".tar"
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(archive_type, os.path.basename(archive_path)))
            except tarfile.ReadError:
                 raise Exception(self._("error_tar_read_error", "Failed to extract .tar/.tar.gz/.tgz archive '{}': Not a valid TAR/GZipped TAR file.").format(os.path.basename(archive_path)))
            except Exception as e:
                raise Exception(self._("error_tar_extraction_error", "Failed to extract .tar/.tar.gz/.tgz archive '{}': {}").format(os.path.basename(archive_path), e))


        elif archive_path_lower.endswith(".tar.bz2"):
            try:
                import bz2
                with tarfile.open(archive_path, 'r:bz2') as tar_ref:
                     tar_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".tar.bz2", os.path.basename(archive_path)))
            except tarfile.ReadError:
                 raise Exception(self._("error_tarbz2_read_error", "Failed to extract .tar.bz2 archive '{}': Not a valid BZ2ipped TAR file.").format(os.path.basename(archive_path)))
            except Exception as e:
                raise Exception(self._("error_tarbz2_extraction_error", "Failed to extract .tar.bz2 archive '{}': {}").format(os.path.basename(archive_path), e))


        elif archive_path_lower.endswith((".xz", ".tar.xz")):
            try:
                import lzma
            except ImportError:
                raise Exception(self._("error_lzma_module_missing", "LZMA module not found. Cannot extract .xz archives."))

            temp_tar_path = os.path.join(dest_path, "temp_lzma_decompressed.tar")
            try:
                with lzma.open(archive_path, 'rb') as f_in:
                    os.makedirs(dest_path, exist_ok=True)
                    with open(temp_tar_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                print(self._("print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".xz", os.path.basename(archive_path)))

                with tarfile.open(temp_tar_path, 'r') as tar_ref:
                    tar_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".xz", os.path.basename(archive_path)))

            except tarfile.ReadError:
                 raise Exception(self._("error_tarxz_invalid_tar", "Decompressed file from .xz archive '{}' is not a valid tar archive. Please ensure it is a .tar.xz file.").format(os.path.basename(archive_path)))
            except Exception as e:
                 raise Exception(self._("error_tarxz_extraction_error", "Failed to decompress or extract .xz archive '{}': {}").format(os.path.basename(archive_path), e))
            finally:
                if os.path.exists(temp_tar_path):
                    try:
                        os.remove(temp_tar_path)
                    except Exception as e:
                        print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")


        elif archive_path_lower.endswith((".lz4", ".tar.lz4")):
            try:
                import lz4.frame
            except ImportError:
                raise Exception(self._("error_lz4_module_missing", "The 'lz4' library is not installed. Please install it using 'pip install lz4'."))

            temp_tar_path = os.path.join(dest_path, "temp_lz4_decompressed.tar")
            try:
                with lz4.frame.open(archive_path, 'rb') as f_in:
                    os.makedirs(dest_path, exist_ok=True)
                    with open(temp_tar_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                print(self._("print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".lz4", os.path.basename(archive_path)))

                with tarfile.open(temp_tar_path, 'r') as tar_ref:
                    tar_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".lz4", os.path.basename(archive_path)))

            except tarfile.ReadError:
                 raise Exception(self._("error_tarlz4_invalid_tar", "Decompressed file from .lz4 archive '{}' is not a valid tar archive. Please ensure it is a .tar.lz4 file.").format(os.path.basename(archive_path)))
            except Exception as e:
                 raise Exception(self._("error_tarlz4_extraction_error", "Failed to decompress or extract .lz4 archive '{}': {}").format(os.path.basename(archive_path), e))
            finally:
                if os.path.exists(temp_tar_path):
                    try:
                        os.remove(temp_tar_path)
                    except Exception as e:
                        print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")


        elif archive_path_lower.endswith((".zst", ".tar.zst")):
            try:
                import zstandard
            except ImportError:
                raise Exception(self._("error_zstd_module_missing", "The 'zstandard' library is not installed. Please install it using 'pip install zstandard'."))

            temp_tar_path = os.path.join(dest_path, "temp_zstd_decompressed.tar")
            try:
                dctx = zstandard.ZstdDecompressor()
                with open(archive_path, 'rb') as f_in, \
                     open(temp_tar_path, 'wb') as f_out:
                     os.makedirs(dest_path, exist_ok=True)
                     dctx.copy_stream(f_in, f_out)

                print(self._("print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".zst", os.path.basename(archive_path)))

                with tarfile.open(temp_tar_path, 'r') as tar_ref:
                    tar_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".zst", os.path.basename(archive_path)))

            except tarfile.ReadError:
                 raise Exception(self._("error_tarzst_invalid_tar", "Decompressed file from .zst archive '{}' is not a valid tar archive. Please ensure it is a .tar.zst file.").format(os.path.basename(archive_path)))
            except Exception as e:
                 raise Exception(self._("error_tarzst_extraction_error", "Failed to decompress or extract .zst archive '{}': {}").format(os.path.basename(archive_path), e))
            finally:
                if os.path.exists(temp_tar_path):
                    try:
                        os.remove(temp_tar_path)
                    except Exception as e:
                        print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")


        elif archive_path_lower.endswith(".7z"):
            try:
                import py7zr
            except ImportError:
                raise Exception(self._("error_py7zr_module_missing", "The 'py7zr' library is not installed. Please install it using 'pip install py7zr'."))

            try:
                with py7zr.SevenZipFile(archive_path, mode='r') as szr:
                    szr.extractall(path=dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".7z", os.path.basename(archive_path)))
            except py7zr.Bad7zFile:
                 raise Exception(self._("error_7z_bad_file", "Failed to extract .7z archive '{}': File is corrupted or not a valid 7z archive.").format(os.path.basename(archive_path)))
            except Exception as e:
                 raise Exception(self._("error_7z_extraction_error", "Failed to extract .7z archive '{}': {}").format(os.path.basename(archive_path), e))

        elif archive_path_lower.endswith(".rar"):
            try:
                import rarfile
            except ImportError:
                raise Exception(self._("error_rarfile_module_missing", "The 'rarfile' library is not installed. Please install it using 'pip install rarfile' and ensure the 'unrar' utility is installed and available in your system's PATH."))

            try:
                with rarfile.RarFile(archive_path, 'r') as rar_ref:
                     rar_ref.extractall(dest_path)
                print(self._("print_extracted_archive", "Extracted {} archive: {}").format(".rar", os.path.basename(archive_path)))
            except rarfile.RarCannotExec as e:
                 raise Exception(self._("error_rar_unrar_not_found", "Failed to extract .rar archive '{}'. The 'unrar' command was not found or could not be executed. Please install 'unrar' and ensure it is available in PATH. Error: {}").format(os.path.basename(archive_path), e))
            except rarfile.RarExtError as e:
                 raise Exception(self._("error_rar_rarfile", "Failed to extract .rar archive '{}'. Rarfile error: {}").format(os.path.basename(archive_path), e))
            except Exception as e:
                 raise Exception(self._("error_rar_unexpected", "An unexpected error occurred while extracting .rar archive '{}': {}").format(os.path.basename(archive_path), e))

        else:
            raise Exception(self._("error_unsupported_archive_format", "Unsupported archive format for extraction: {}").format(os.path.basename(archive_path)))


    def find_theme_txt(self, root_dir):
        if not os.path.isdir(root_dir):
             return None
        for root, dirs, files in os.walk(root_dir):
            if "theme.txt" in files:
                return os.path.join(root, "theme.txt")
        return None

    def find_pf2_fonts(self, root_dir):
        fonts = set()
        if not os.path.isdir(root_dir):
             return fonts

        drive_display = self.drive_var.get()
        drive = extract_drive_letter(drive_display)
        if not drive:
             print(self._("error_extracting_drive_letter", "Error: Could not extract drive letter from '{}'").format(display_string=drive_display))
             return fonts

        for root, dirs, files in os.walk(root_dir):
            for f in files:
                if f.lower().endswith(".pf2"):
                     try:
                         rel_path = os.path.relpath(os.path.join(root, f), drive).replace("\\", "/")
                         fonts.add(f"/{rel_path}")
                     except ValueError:
                         print(self._("print_warning_could_not_get_font_path", "Warning: Could not get relative path for font file: {}").format(os.path.join(root, f)))
                         pass

        return fonts

    def load_existing_themes(self):

        drive_display = self.drive_var.get()
        if not drive_display:
            self.theme_display_names_from_json = []
            self.root.after(0, self.default_theme_combo.config, {'values': []})
            self.root.after(0, self.default_theme_var.set, "")
            self.root.after(0, self.remove_theme_combo.config, {'values': []})
            self.root.after(0, self.remove_theme_combo.set, "")
            self.resolution_var.set("")
            return
        self.current_drive = extract_drive_letter(drive_display)
        if not self.current_drive:
            print(self._("error_extracting_drive_letter", "Error: Could not extract drive letter from '{}'").format(display_string=drive_display))
            self.theme_display_names_from_json = []
            self.root.after(0, self.default_theme_combo.config, {'values': []})
            self.root.after(0, self.default_theme_var.set, "")
            self.root.after(0, self.remove_theme_combo.config, {'values': []})
            self.root.after(0, self.remove_theme_combo.set, "")
            self.resolution_var.set("")
            return


        json_path = os.path.join(self.current_drive, VENTOY_JSON_PATH)

        self.theme_display_names_from_json = []
        config = {}
        default_theme_set = False
        resolution_set = False
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                     config = json.load(f)

                theme_config = config.get('theme', {})
                theme_files = theme_config.get('file', [])
                self.theme_display_names_from_json = [os.path.basename(os.path.dirname(p)) for p in theme_files if p and os.path.dirname(p)]
                values_default_combo = self.theme_display_names_from_json.copy()
                values_default_combo.insert(0, self._("option_random_theme", "Random Theme"))
                self.root.after(0, self.default_theme_combo.config, {'values': values_default_combo})
                current_default_index_1_based = theme_config.get('default_file', 0)
                if current_default_index_1_based == 0:
                    self.default_theme_var.set(self._("option_random_theme", "Random Theme"))
                    default_theme_set = True
                elif 0 < current_default_index_1_based <= len(theme_files):
                    try:
                         path_in_json = theme_files[current_default_index_1_based - 1]
                         theme_name_from_path = os.path.basename(os.path.dirname(path_in_json)) if os.path.dirname(path_in_json) else ""
                         if theme_name_from_path and theme_name_from_path in self.theme_display_names_from_json:
                              self.default_theme_var.set(theme_name_from_path)
                              default_theme_set = True
                         else:
                              print(self._("print_warning_default_file_index_invalid", "Warning: default_file index {} in ventoy.json points to an invalid theme path/name. Resetting to Random.").format(current_default_index_1_based))
                              self.default_theme_var.set(self._("option_random_theme", "Random Theme"))
                              default_theme_set = True

                    except IndexError:
                         print(self._("print_warning_invalid_default_file_index", "Warning: Invalid default_file index ({}) in ventoy.json. Resetting to Random Theme.").format(current_default_index_1_based))
                         self.default_theme_var.set(self._("option_random_theme", "Random Theme"))
                         default_theme_set = True
                    except Exception as e:
                         print(self._("print_error_finding_theme_index", "Error finding theme index in JSON: {}").format(e))
                         self.default_theme_var.set(self._("option_random_theme", "Random Theme"))
                         default_theme_set = True

                else:
                     print(self._("print_warning_invalid_default_file_index", "Warning: Invalid default_file index ({}) in ventoy.json. Resetting to Random Theme.").format(current_default_index_1_based))
                     self.default_theme_var.set(self._("option_random_theme", "Random Theme"))
                     default_theme_set = True
                current_resolution = theme_config.get('gfxmode', 'max')
                if current_resolution in self.resolution_combo['values']:
                    self.resolution_var.set(current_resolution)
                    resolution_set = True
                else:
                     print(self._("print_warning_invalid_gfxmode", "Warning: Invalid 'gfxmode' value '{}' in ventoy.json. Setting to max.").format(current_resolution))
                     self.resolution_var.set('max')
                     resolution_set = True


            except json.JSONDecodeError:
                print(self._("print_warning_could_not_parse_json", "Warning: Could not parse ventoy.json on {}. File might be corrupted or not a valid JSON.").format(self.current_drive))
                self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))
                self.root.after(0, self.resolution_var.set, "")

            except PermissionError:
                print(self._("print_warning_permission_denied_read_json", "Warning: Permission denied while reading ventoy.json on {}.").format(self.current_drive))
                self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))
                self.root.after(0, self.resolution_var.set, "")

            except Exception as e:
                print(self._("print_warning_failed_read_json_settings", "Warning: Failed to read ventoy.json settings from {}: {}").format(self.current_drive, e))
                self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))
                self.root.after(0, self.resolution_var.set, "")

        else:
            self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))
            self.root.after(0, self.resolution_var.set, "")
        themes_disk_path = os.path.join(self.current_drive, THEMES_DIR_NAME)
        themes_on_disk_names = []
        if os.path.exists(themes_disk_path) and os.path.isdir(themes_disk_path):
             try:
                 themes_on_disk_names = [item for item in os.listdir(themes_disk_path) if os.path.isdir(os.path.join(themes_disk_path, item))]
             except PermissionError:
                  print(self._("print_warning_permission_denied_listing_themes", "Warning: Permission denied while listing theme directory on {}.").format(self.current_drive))
             except Exception as e:
                  print(self._("print_warning_error_listing_themes", "Warning: Error listing theme directory on {}: {}").format(self.current_drive, e))
        values_remove_combo = [self._("option_select_theme_to_delete", "Select a theme to delete")]
        values_remove_combo.extend(themes_on_disk_names)
        self.root.after(0, self.remove_theme_combo.config, {'values': values_remove_combo})
        self.root.after(0, self.remove_theme_combo.set, self._("option_select_theme_to_delete", "Select a theme to delete"))
        
    def on_drive_selected(self, event=None):
        self.reset_status()
        self.load_existing_themes()

    def update_usb_drives(self):
        values = list_drives_display()
        current_drive = self.drive_var.get()

        for combo in self.drive_combos:
            if combo and combo.winfo_exists():
                 combo['values'] = values

        if current_drive and current_drive in values:
             self.drive_var.set(current_drive)
        else:
             self.drive_var.set("")

        self.on_drive_selected()

    def add_drive_selector(self, parent):
       
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(OUTER_PADDING, 0))

        title_label = ttk.Label(main_frame, text=self._("device_label", "Device"), style="Courier.TLabel") 
        title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")

        self.translatable_widgets.append((title_label, "device_label"))


        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="x", padx=INNER_PADDING, pady=0)

        combo = ttk.Combobox(
            content_frame,
            textvariable=self.drive_var, 
            postcommand=self.update_usb_drives, 
            state="readonly", 
            style="Courier.TCombobox"
        )
        combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)

        combo.bind("<<ComboboxSelected>>", self.on_drive_selected)

        if not hasattr(self, 'drive_combos'):
             self.drive_combos = []
        self.drive_combos.append(combo)

    def browse_zip(self):

        paths = filedialog.askopenfilenames(
            title=self._("dialog_select_theme_archives_title", "Select Theme Archive(s)"),
            filetypes=[("Theme Archives", "*.zip *.tar *.gz *.tgz *.xz *.rar *.7z *.zipx *.tar.bz2 *.tar.lz4 *.tar.zst"), ("All files", "*.*")]
        )
        for path in paths:
            if path and os.path.isfile(path):
                if path not in self.theme_sources_paths:
                    self.theme_sources_paths.append(path)
                    file_name = os.path.basename(path)
                    display_name = self._get_truncated_name(file_name)
                    self.theme_listbox.insert(tk.END, display_name)
                else:
                    print(self._("print_skipping_already_added_file", "Warning: Skipping already added file: {}").format(path))
            elif path:
                print(self._("print_skipped_non_file_selection", "Warning: Skipping non-file selection: {}").format(path))


    def on_drop(self, event):
        """Handles files and directories dropped onto the install tab."""
        paths = self.root.tk.splitlist(event.data) 
        supported_archive_extensions = ('.zip', '.tar', '.tar.gz', '.tgz', '.xz', '.rar', '.7z', '.zipx', '.tar.bz2', '.tar.lz4', '.tar.zst')
        total_processed_count = 0 


        for path in paths: 
            path = os.path.normpath(path) 
            processed_count_in_this_item = 0 
            if os.path.isdir(path):

                print(self._("print_dropped_directory", "Dropped directory: {}").format(path))

                potential_sources_to_add = [] 
                found_archives_in_root = []
                try:
                    if os.path.exists(path): 
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            if os.path.isfile(item_path) and item.lower().endswith(supported_archive_extensions):
                                 found_archives_in_root.append(item_path)
                except PermissionError:
                     print(self._("print_warning_permission_denied_list_dir", "Warning: Permission denied listing directory: {}").format(path))
                     self.show_message_safe("warning", "warning_permission_denied_title", "warning_permission_denied_message", path)
                     continue 
                except Exception as e:
                     print(f"Error listing directory {path}: {e}")
                     self.show_message_safe("error", "error_listing_directory_title", "error_listing_directory_message", path, e)
                     continue


                if found_archives_in_root:
                    print("Detected folder containing archives:", path)
                    potential_sources_to_add.extend(found_archives_in_root)
                    directory_content_type = "archives_in_root"

                else:
                    found_theme_subfolders = []
                    try:
                        if os.path.exists(path):
                             for item in os.listdir(path):
                                item_path = os.path.join(path, item)
                                if os.path.isdir(item_path):
                                     if self.find_theme_txt(item_path):
                                         found_theme_subfolders.append(item_path)

                    except PermissionError:
                         print(self._("print_warning_permission_denied_list_dir", "Warning: Permission denied listing directory: {}").format(path))
                         self.show_message_safe("warning", "warning_permission_denied_title", "warning_permission_denied_message", path)
                         continue 
                    except Exception as e:
                         print(f"Error checking subdirectories in {path}: {e}")
                         self.show_message_safe("error", "error_listing_directory_title", "error_listing_directory_message", path, e)
                         continue


                    if found_theme_subfolders:
                        print("Detected folder containing theme folders:", path)
                        potential_sources_to_add.extend(found_theme_subfolders)
                        directory_content_type = "theme_folders_in_subdirs"

                    else:
                        if self.find_theme_txt(path):
                             print("Detected dropped folder is a single theme folder:", path)
                             potential_sources_to_add.append(path)
                             directory_content_type = "single_theme_folder"

                        else:
                             print(self._("warning_skipping_directory_content_warning", "Skipping directory '{}' as it does not contain supported theme archives or theme folders.").format(os.path.basename(path)))
                             self.root.after(0, messagebox.showwarning,
                                             self._("warning_skipping_directory_title", "Skipping Directory"),
                                             self._("warning_skipping_directory_content_warning", "Skipping directory '{}' as it does not contain supported theme archives or theme folders.").format(os.path.basename(path)))
                             directory_content_type = "skipped_no_content" 
                             pass 

                if potential_sources_to_add:
                    for source_path in potential_sources_to_add:
                         if source_path not in self.theme_sources_paths:
                            self.theme_sources_paths.append(source_path)
                            if os.path.isfile(source_path): 
                                file_name = os.path.basename(source_path)
                                display_name = self._get_truncated_name(file_name)
                                self.root.after(0, self.theme_listbox.insert, tk.END, display_name)
                                print("Added archive source from directory:", source_path)
                            elif os.path.isdir(source_path):
                                 folder_name = os.path.basename(source_path)
                                 display_name = self._get_truncated_name(folder_name)
                                 folder_prefix = self._("listbox_folder_prefix", "[FOLDER]")
                                 self.root.after(0, self.theme_listbox.insert, tk.END, f"{folder_prefix} {display_name}")
                                 print("Added theme folder source from directory:", source_path)
                            processed_count_in_this_item += 1 
                         else:
                             print("Warning: Skipping already added source from directory:", source_path)
                             
                if directory_content_type != "skipped_no_content": 
                     if processed_count_in_this_item > 0:

                         if directory_content_type == "archives_in_root":
                             msg_key = "status_added_dropped_archives_from_folder" 
                             default_msg = "Added {} archive(s) from dropped folder '{}'."
                             self.update_status_safe(0, self._(msg_key, default_msg).format(processed_count_in_this_item, os.path.basename(path)), 0)
                         elif directory_content_type == "theme_folders_in_subdirs":
                              msg_key = "status_added_dropped_theme_folders_from_folder" 
                              default_msg = "Added {} theme folder(s) from dropped folder '{}'."
                              self.update_status_safe(0, self._(msg_key, default_msg).format(processed_count_in_this_item, os.path.basename(path)), 0)
                         elif directory_content_type == "single_theme_folder":
                              msg_key = "status_added_dropped_single_theme_folder" 
                              default_msg = "Added theme folder '{}'."

                              self.update_status_safe(0, self._(msg_key, default_msg).format(os.path.basename(path)), 0)


            elif os.path.isfile(path):

                if path.lower().endswith(supported_archive_extensions):
                    if path not in self.theme_sources_paths:
                        self.theme_sources_paths.append(path)
                        file_name = os.path.basename(path)
                        display_name = self._get_truncated_name(file_name)
                        self.root.after(0, self.theme_listbox.insert, tk.END, display_name)
                        print(self._("print_added_theme_archive_source", "Added theme archive source: {}").format(path))
                        processed_count_in_this_item += 1 
                        print(self._("print_skipping_already_added_file", "Warning: Skipping already added file: {}").format(path))
                else:
                    print(self._("print_skipping_unsupported_file_extension", "Warning: Skipping unsupported file extension: {}").format(os.path.basename(path)))
            else:
                print(self._("print_skipping_unsupported_dropped_item", "Warning: Skipping unsupported dropped item: {}").format(path))

            total_processed_count += processed_count_in_this_item 

        if total_processed_count > 0:

             self.update_status_safe(0, self._("status_added_dropped_items_total", "Added {} item(s).").format(total_processed_count), 0) # Новый ключ
        elif total_processed_count == 0 and paths: 
             self.update_status_safe(0, self._("status_no_supported_dropped_items", "No supported items found in dropped items."), 0)

    def add_install_tab_widgets(self):
        main_frame = ttk.Frame(self.install_tab)
        main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
        main_frame.drop_target_register(DND_FILES)
        main_frame.dnd_bind('<<Drop>>', self.on_drop)
        title_label = ttk.Label(main_frame, text=self._("install_source_label", "Browse or Drag & Drop Theme Archives"), style="Courier.TLabel")
        title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
        self.translatable_widgets.append((title_label, "install_source_label"))


        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

        list_scroll_frame = ttk.Frame(content_frame)
        list_scroll_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.theme_listbox = tk.Listbox(list_scroll_frame,
                                         height=5,
                                         selectmode=tk.MULTIPLE,
                                         width=35,
                                         yscrollcommand=scrollbar.set)
        self.theme_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=self.theme_listbox.yview)

        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(side="left", padx=(WIDGET_SPACING, 0), pady=0)
        self.browse_btn_install = ttk.Button(btn_frame,
                                             text=self._("browse_button", "Browse"),
                                             command=self.browse_zip,
                                             style="RoundedButton.TButton",
                                             takefocus=False)
        self.browse_btn_install.pack(pady=(0, BUTTON_GROUP_SPACING))
        self.translatable_widgets.append((self.browse_btn_install, "browse_button"))
        self.clear_btn_install = ttk.Button(btn_frame,
                                            text=self._("clear_button", "Clear"),
                                            command=self.clear_zip_selection,
                                            style="RoundedButton.TButton",
                                            takefocus=False)
        self.clear_btn_install.pack()
        self.translatable_widgets.append((self.clear_btn_install, "clear_button"))
        self.status_label_install = tk.Label(self.install_tab, textvariable=self.status_bar_install, anchor="w", font=("Courier New", 10))
        self.status_label_install.place(x=5, y=220, width=425)

        self.progress_bar_install = ttk.Progressbar(self.install_tab, mode='determinate', variable=self.progress_value_install)
        self.progress_bar_install.place(x=5, y=250, width=425)
        self.apply_btn_install = ttk.Button(self.install_tab,
                                             text=self._("apply_themes_button", "Apply Themes"),
                                             command=self.start_apply_theme_thread,
                                             style="RoundedButton.TButton",
                                             width=15,
                                             takefocus=False)
        self.apply_btn_install.place(x=136, y=282)
        self.translatable_widgets.append((self.apply_btn_install, "apply_themes_button"))

    def add_settings_tab_widgets(self):
        default_theme_main_frame = ttk.Frame(self.settings_tab)
        default_theme_main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
        default_theme_title_label = ttk.Label(default_theme_main_frame, text=self._("select_default_theme_label", "Select Default Theme"), style="Courier.TLabel")
        default_theme_title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
        self.translatable_widgets.append((default_theme_title_label, "select_default_theme_label"))

        default_theme_content_frame = ttk.Frame(default_theme_main_frame)
        default_theme_content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

        combo_button_frame = ttk.Frame(default_theme_content_frame)
        combo_button_frame.pack(fill="x", padx=0, pady=0)

        self.default_theme_combo = ttk.Combobox(combo_button_frame,
                                                 textvariable=self.default_theme_var,
                                                 state="readonly",
                                                 style="Courier.TCombobox")
        self.default_theme_combo.pack(side="left", fill="x", expand=True, padx=0, pady=WIDGET_SPACING)
        self.default_theme_combo.bind("<<ComboboxSelected>>", self.on_default_theme_selected)

        resolution_main_frame = ttk.Frame(self.settings_tab)
        resolution_main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
        resolution_title_label = ttk.Label(resolution_main_frame, text=self._("choose_resolution_label", "Choose Standard Resolution"), style="Courier.TLabel")
        resolution_title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
        self.translatable_widgets.append((resolution_title_label, "choose_resolution_label"))

        resolution_content_frame = ttk.Frame(resolution_main_frame)
        resolution_content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

        self.resolution_combo = ttk.Combobox(resolution_content_frame,
                                             textvariable=self.resolution_var,
                                             state="readonly",
                                             style="Courier.TCombobox")
        self.resolution_combo['values'] = [
            "max", "3840x2160", "2560x1440", "1920x1080", "1680x1050", "1600×900",
            "1440x900", "1280x1024", "1280x960", "1024x768", "800x600"
        ]
        self.resolution_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)

        self.apply_btn_settings = ttk.Button(self.settings_tab,
                                             text=self._("apply_settings_button", "Apply settings"),
                                             command=self.start_apply_settings_thread,
                                             style="RoundedButton.TButton",
                                             width=15,
                                             takefocus=False)
        self.apply_btn_settings.place(x=136, y=282)
        self.translatable_widgets.append((self.apply_btn_settings, "apply_settings_button"))

    def add_remove_tab_widgets(self):
        main_frame = ttk.Frame(self.remove_tab)
        main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, SECTION_SPACING))
        title_label = ttk.Label(main_frame, text=self._("remove_theme_label", "Choose Theme to Delete"), style="Courier.TLabel")
        title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
        self.translatable_widgets.append((title_label, "remove_theme_label"))

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)
        self.remove_theme_combo = ttk.Combobox(content_frame,
                                                 state="readonly",
                                                 style="Courier.TCombobox")
        self.remove_theme_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)
        self.status_label_remove = tk.Label(self.remove_tab, textvariable=self.status_bar_remove, anchor="w", font=("Courier New", 10))
        self.status_label_remove.place(x=5, y=220, width=425)

        self.progress_bar_remove = ttk.Progressbar(self.remove_tab, mode='determinate', variable=self.progress_value_remove)
        self.progress_bar_remove.place(x=5, y=250, width=425)
        self.remove_btn = ttk.Button(self.remove_tab,
                                     text=self._("remove_selected_button", "Remove Selected Theme"),
                                     command=self.start_remove_theme_thread,
                                     style="RoundedButton.TButton",
                                     width=21,
                                     takefocus=False)
        self.remove_btn.place(x=230, y=282)
        self.translatable_widgets.append((self.remove_btn, "remove_selected_button"))
        self.remove_all_btn = ttk.Button(self.remove_tab,
                                         text=self._("remove_all_button", "Remove ALL THEMES"),
                                         command=self.start_remove_all_themes_thread,
                                         style="RoundedButton.TButton",
                                         width=21,
                                         takefocus=False)
        self.remove_all_btn.place(x=10, y=282)
        self.translatable_widgets.append((self.remove_all_btn, "remove_all_button"))

    def add_language_tab_widgets(self):
        main_frame = ttk.Frame(self.language_tab)
        main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))

        self.select_language_label = ttk.Label(main_frame, text=self._("select_language_label", "Select Language"), style="Courier.TLabel")
        self.select_language_label.pack(padx=INNER_PADDING, pady=(5, TITLE_SPACING), anchor="w")
        self.translatable_widgets.append((self.select_language_label, "select_language_label"))

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="x", padx=INNER_PADDING, pady=0)

        language_names = [lang.get('name', f"Unnamed Language {i+1}") for i, lang in enumerate(self.all_translations) if isinstance(lang, dict)]

        language_names.sort()


        self.language_combo = ttk.Combobox(
            content_frame,
            textvariable=self.language_var,
            values=language_names, 
            state="readonly",
            style="Courier.TCombobox"
        )
        self.language_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_selected)
       
        version_frame = ttk.Frame(self.language_tab)

        frame_relx = 1.0 
        frame_rely = 0.5
        
        offset_x = -10
        frame_y = 315
        selected_anchor = 'e'

        version_frame.place(
            relx=frame_relx,
            y=frame_y, 
            x=offset_x, 
            anchor=selected_anchor
        )
            

        format_string = self._("app_version_label", "Version: {}")
        try:
             version_text = format_string.format(self.app_version)
        except Exception as e:
             print(f"Error formatting version text: {e}")
             version_text = f"Formatting Error: {e}" 

        self.app_version_label = ttk.Label(
            version_frame, 
            text=version_text,
            style="Courier.TLabel"
        )
        self.app_version_label.pack(padx=0, pady=0, anchor="w") 
        self.translatable_widgets.append((self.app_version_label, "app_version_label"))
        
    def on_language_selected(self, event=None):

        selected_name = self.language_var.get()

        selected_translation = None
        for lang_dict in self.all_translations:
            if isinstance(lang_dict, dict) and lang_dict.get('name') == selected_name:
                selected_translation = lang_dict
                break

        if selected_translation and selected_translation is not self._messages:
            self._messages = selected_translation
            print(f"Language changed to: {selected_name}")
            self.update_gui_language()
            self.on_drive_selected()

        elif not selected_translation and selected_name:
            print(f"Error: Selected language '{selected_name}' not found in translations list.")
            self.show_message_safe("error", "language_change_error_title", "language_change_error_message", selected_name=selected_name)

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)
        self.install_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.remove_tab = ttk.Frame(self.notebook)
        self.language_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.install_tab, text=self._("install_tab_title", "Install Themes"))
        self.notebook.add(self.settings_tab, text=self._("settings_tab_title", "Themes Settings"))
        self.notebook.add(self.remove_tab, text=self._("remove_tab_title", "Remove Themes"))
        self.notebook.add(self.language_tab, text=self._("language_tab_title", "Language"))
        self.add_drive_selector(self.install_tab)
        self.add_drive_selector(self.settings_tab)
        self.add_drive_selector(self.remove_tab)
        self.add_install_tab_widgets()
        self.add_settings_tab_widgets()
        self.add_remove_tab_widgets()
        self.add_language_tab_widgets()
        self.add_footer_links()

    def apply_theme_task(self, drive, theme_sources_paths):

        try:
            total = len(theme_sources_paths)
            if total == 0:
                self.update_status_safe(0, self._("status_no_theme_items_warning_message", "No theme items to process."), 100)
                return

            all_paths = set()
            all_fonts = set()
            for i, source_path in enumerate(theme_sources_paths):
                processed_count = i + 1
                if not os.path.exists(source_path):
                    self.update_status_safe(0, self._("status_skipped_missing_source", "Skipping missing source: {}").format(os.path.basename(source_path)), 100 * i / total)
                    self.show_message_safe("warning", "warning_source_not_found_title", "warning_source_not_found_message",
                                           title_key=self._("warning_source_not_found_title", "Source Not Found"),
                                           message_key=self._("warning_source_not_found_message", "Theme source not found: {}. Skipping.").format(os.path.basename(source_path)))
                    continue
                theme_name = os.path.splitext(os.path.basename(source_path))[0] if os.path.isfile(source_path) else os.path.basename(source_path)
                theme_dir = os.path.join(drive, THEMES_DIR_NAME, theme_name)

                should_process = True
                if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
                    self.update_status_safe(0, self._("status_confirming_overwrite", "Confirming overwrite for {}...").format(theme_name), 100 * (i / total))
                    result_queue = queue.Queue(maxsize=1)
                    self.root.after(0, self._show_overwrite_dialog_threaded, theme_name, result_queue)
                    try:
                        overwrite_confirmed = result_queue.get(block=True)
                        print(f"Received confirmation for '{theme_name}': {overwrite_confirmed}")
                        if not overwrite_confirmed:
                            should_process = False
                    except Exception as e:
                        print(f"Error while waiting for overwrite confirmation for '{theme_name}': {e}")
                        self.show_message_safe("error", "error_task_title", "error_task_message",
                                               title_key=self._("error_task_title", "Task Error"),
                                               message_key=self._("error_task_message", "An unexpected error occurred during task: {}\\n{}").format(f"Failed to get confirmation for theme '{theme_name}'. Skipping this theme.", ""),
                                               args=[])
                        should_process = False
                if should_process:
                    try:
                        if os.path.isdir(theme_dir):
                            if os.path.isdir(source_path):
                                print(f"Overwriting existing theme directory: {theme_dir}")
                                try:
                                    shutil.rmtree(theme_dir)
                                    print(self._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_dir))
                                except Exception as clean_e:
                                    raise Exception(f"Failed to remove existing theme directory '{theme_name}' before overwrite: {clean_e}")
                        if os.path.isfile(source_path):
                            os.makedirs(theme_dir, exist_ok=True)
                            self.update_status_safe(0, self._("status_extracting", "Extracting {}...").format(theme_name), 100 * (i / total))
                            self.extract_theme(source_path, theme_dir)
                        elif os.path.isdir(source_path):
                            self.update_status_safe(0, self._("status_copying", "Copying theme folder {}...").format(theme_name), 100 * (i / total))
                            try:
                                shutil.copytree(source_path, theme_dir)
                                print(self._("print_copied_theme_folder", "Copied theme folder: {} to {}").format(source_path, theme_dir))
                            except Exception as copy_e:
                                raise Exception(f"Failed to copy theme folder '{theme_name}': {copy_e}")
                        theme_txt = self.find_theme_txt(theme_dir)
                        if not theme_txt:
                            self.show_message_safe("warning", "warning_theme_txt_not_found_title", "warning_theme_txt_not_found_message",
                                                   title_key=self._("warning_theme_txt_not_found_title", "Warning"),
                                                   message_key=self._("warning_theme_txt_not_found_message", "theme.txt not found in processed theme '{}'. This theme might not work correctly.").format(theme_name))
                            if os.path.exists(theme_dir):
                                 rel_theme_dir = os.path.relpath(theme_dir, drive).replace("\\", "/")
                                 all_paths.add(f"/{rel_theme_dir}")
                        else:
                            rel_path = os.path.relpath(theme_txt, drive).replace("\\", "/")
                            all_paths.add(f"/{rel_path}")
                        all_fonts.update(self.find_pf2_fonts(theme_dir))
                        self.update_status_safe(0, self._("status_processed", "Processed {}").format(theme_name), 100 * processed_count / total)

                    except Exception as e:
                         error_message = self._("error_processing_theme_message", "Error processing theme '{}': {}").format(theme_name, e)
                         print(error_message)
                         self.show_message_safe("error", "error_processing_theme_title", "",
                                                title_key=self._("error_processing_theme_title", "Processing Error"),
                                                message_key="",
                                                args=[error_message])
                         self.update_status_safe(0, self._("status_error_processing_theme", "Error processing {}").format(theme_name), 100 * processed_count / total)
                         continue

                else:
                     self.update_status_safe(0, self._("status_skipped_existing_theme", "Skipped existing theme: {}").format(theme_name), 100 * processed_count / total)
                     continue
            json_path = os.path.join(drive, VENTOY_JSON_PATH)
            config = {}
            if os.path.exists(json_path):
                try:
                    print(self._("print_loaded_existing_json", "Loaded existing ventoy.json"))
                    with open(json_path, 'r', encoding='utf-8') as f:
                         config = json.load(f)
                except Exception as e:
                    self.show_message_safe("error", "error_json_read_title", "error_json_read_message_existing",
                                           title_key=self._("error_json_read_title", "JSON Read Error"),
                                           message_key=self._("error_json_read_message_existing", "Failed to read existing ventoy.json: {}. Creating a new one.").format(e),
                                           args=[])
                    config = {}
            config.setdefault('theme', {})
            theme_config = config['theme']
            theme_config.setdefault('file', [])
            theme_config.setdefault('default_file', 0)
            theme_config.setdefault('gfxmode', 'max')
            theme_config.setdefault('display_mode', 'GUI')
            theme_config.setdefault('serial_param', '--unit=0 --speed=9600')
            theme_config.setdefault('fonts', [])
            theme_config.setdefault('images', [])
            theme_config['file'] = sorted(list(set(theme_config.get('file', [])) | all_paths))
            theme_config['fonts'] = sorted(list(set(theme_config.get('fonts', [])) | all_fonts))
            self.update_status_safe(0, self._("status_updating_json", "Updating ventoy.json..."), 100)
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                print(self._("print_saved_json_successfully", "Saved ventoy.json successfully."))
                self.update_status_safe(0, self._("status_themes_applied_success", "Themes applied and config updated successfully!"), 100)
                self.root.after(0, self.load_existing_themes)

            except Exception as e:
                self.show_message_safe("error", "error_json_write_title", "error_json_write_message",
                                       title_key=self._("error_json_write_title", "JSON Write Error"),
                                       message_key=self._("error_json_write_message", "Failed to save ventoy.json: {}.").format(e),
                                       args=[])
                self.update_status_safe(0, self._("status_task_failed", "Task failed."), 100)


        except Exception as e:
             error_message = self._("error_task_message", "An unexpected error occurred during task: {}\\n{}").format(str(e), traceback.format_exc())
             print(error_message)
             self.show_message_safe("error", "error_task_title", "",
                                    title_key=self._("error_task_title", "Task Error"),
                                    message_key="",
                                    args=[error_message])
             self.update_status_safe(0, self._("status_apply_theme_task_failed", "Theme application task failed."), 100)

        finally:
            self.set_buttons_state(tk.NORMAL)
            self.root.after(500, lambda: self.update_status_safe(0, self._("status_ready", "Status - READY"), 0))

    def start_apply_theme_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_message_safe("warning", "warning_busy_title", "warning_busy_message",
                                   title_key=self._("warning_busy_title", "Busy"),
                                   message_key=self._("warning_busy_message", "Another operation is already in progress."))
            return

        drive_display = self.drive_var.get()
        if not drive_display:
            self.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message",
                                   title_key=self._("warning_select_drive_title", "Warning"),
                                   message_key=self._("warning_select_drive_message", "Please select a drive first."))
            return

        if not self.theme_sources_paths:
            self.show_message_safe("warning", "warning_select_drive_title", "warning_no_theme_archive_selected_message",
                                   title_key=self._("warning_select_drive_title", "Warning"),
                                   message_key=self._("warning_no_theme_archive_selected_message", "No theme archive selected"))
            return

        self.current_drive = extract_drive_letter(drive_display)
        if not self.current_drive:
             self.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message",
                                    title_key=self._("error_drive_letter_title", "Error"),
                                    message_key=self._("error_drive_letter_message", "Could not determine drive letter."))
             return

        self.reset_status()
        self.set_buttons_state(tk.DISABLED)
        self.worker_thread = threading.Thread(target=self.apply_theme_task, args=(self.current_drive, self.theme_sources_paths.copy()))
        self.worker_thread.start()

    def apply_settings_task(self, drive):

        try:
            json_path = os.path.join(drive, VENTOY_JSON_PATH)
            if not os.path.exists(json_path):
                 self.show_message_safe("warning", "warning_ventoy_json_not_found_settings_title", "warning_ventoy_json_not_found_settings_message")
                 return
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                     config = json.load(f)
            except json.JSONDecodeError:
                self.show_message_safe("error", "error_json_read_settings_title", "error_json_read_settings_message", drive=drive)
                return
            except PermissionError:
                self.show_message_safe("error", "permission_error_title", "error_permission_read_json_settings_message", drive=drive)
                return
            except Exception as e:
                 self.show_message_safe("error", "generic_error_title", "error_unexpected_read_json_settings_message", str(e))
                 return
            config.setdefault('theme', {})
            theme_config = config['theme']
            sel = self.default_theme_var.get()
            theme_paths_in_json = theme_config.get('file', [])
            theme_names_in_json = [os.path.basename(os.path.dirname(p)) for p in theme_paths_in_json if p and os.path.dirname(p)]
            if sel == self._("option_random_theme", "Random Theme"):
                theme_config['default_file'] = 0
            elif sel and sel in theme_names_in_json:
                 try:
                      target_suffix_txt = f"/{sel}/theme.txt"
                      target_suffix_dir = f"/{sel}"

                      index_in_json = -1
                      for i, p in enumerate(theme_paths_in_json):
                          if not p or not isinstance(p, str):
                              continue
                          p_lower = p.lower().replace("\\", "/")
                          target_suffix_txt_lower = target_suffix_txt.lower().replace("\\", "/")
                          target_suffix_dir_lower = target_suffix_dir.lower().replace("\\", "/")
                          if p_lower.endswith(target_suffix_txt_lower) or p_lower == target_suffix_dir_lower:
                              index_in_json = i
                              break

                      if index_in_json != -1:
                          theme_config['default_file'] = index_in_json + 1
                      else:
                          print(self._("print_warning_selected_default_theme_not_found_load", "Selected default theme '{}' not found in ventoy.json. Resetting to Random Theme.").format(sel))
                          theme_config['default_file'] = 0
                          self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))

                 except Exception as e:
                      print(self._("print_error_finding_theme_index", "Error finding theme index in JSON: {}").format(e))
                      theme_config['default_file'] = 0
                      self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))


            else:
                 self.show_message_safe("warning", "warning_select_drive_title", "warning_selected_default_theme_not_found", sel)
                 if self._("option_random_theme", "Random Theme") not in self.default_theme_combo['values']:
                      current_values = list(self.default_theme_combo['values'])
                      current_values.insert(0, self._("option_random_theme", "Random Theme"))
                      self.root.after(0, self.default_theme_combo.config, {'values': current_values})
                 self.root.after(0, self.default_theme_var.set, self._("option_random_theme", "Random Theme"))
                 theme_config['default_file'] = 0
            resolution = self.resolution_var.get()
            if resolution in self.resolution_combo['values']:
                 theme_config['gfxmode'] = resolution
            else:
                 print(self._("warning_resolution_not_in_list", "Warning: Selected resolution '{resolution}' is not in the allowed list. Keeping current or default.").format(resolution=resolution))
                 if 'gfxmode' not in theme_config or theme_config['gfxmode'] not in self.resolution_combo['values']:
                      theme_config['gfxmode'] = 'max'
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                     json.dump(config, f, indent=4)
                self.root.after(0, self.load_existing_themes)

            except PermissionError:
                self.show_message_safe("error", "permission_error_title", "error_permission_write_json_settings_message", drive=drive)
                return
            except Exception as e:
                self.show_message_safe("error", "error_unexpected_settings_title", "error_unexpected_write_json_settings_message", str(e))
                return


        except Exception as e:
             self.show_message_safe("error", "error_unexpected_settings_title", "error_unexpected_settings_message", str(e), traceback.format_exc())

        finally:
            self.set_buttons_state(tk.NORMAL)

    def start_apply_settings_thread(self):
         if self.worker_thread and self.worker_thread.is_alive():
             self.show_message_safe("warning", "warning_busy_title", "warning_busy_message",
                                    title_key=self._("warning_busy_title", "Busy"),
                                    message_key=self._("warning_busy_message", "Another operation is already in progress."))
             return

         drive_display = self.drive_var.get()
         if not drive_display:
             self.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message",
                                    title_key=self._("warning_select_drive_title", "Warning"),
                                    message_key=self._("warning_select_drive_message", "Please select a drive first."))
             return

         self.current_drive = extract_drive_letter(drive_display)
         if not self.current_drive:
              self.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message",
                                     title_key=self._("error_drive_letter_title", "Error"),
                                     message_key=self._("error_drive_letter_message", "Could not determine drive letter."))
              return

         self.set_buttons_state(tk.DISABLED)
         self.worker_thread = threading.Thread(target=self.apply_settings_task, args=(self.current_drive,))
         self.worker_thread.start()

    def remove_theme_task(self, drive, selected_theme):

        try:
            json_path = os.path.join(drive, VENTOY_JSON_PATH)
            theme_dir = os.path.join(drive, THEMES_DIR_NAME, selected_theme)
            MAX_STATUS_LENGTH = 50
            prefix_del = self._("status_deleting_theme_prefix", "Deleting theme '")
            suffix_del = self._("status_deleting_theme_suffix", "'...")
            available_length_del = MAX_STATUS_LENGTH - len(prefix_del) - len(suffix_del)
            short_name_del = selected_theme if len(selected_theme) <= available_length_del else selected_theme[:available_length_del - 3] + "..."
            self.update_status_safe(2, f"{prefix_del}{short_name_del}{suffix_del}", 10)
            try:
                if os.path.exists(theme_dir):
                    shutil.rmtree(theme_dir)
                    print(self._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_dir))
                else:
                    print(self._("print_warning_theme_folder_not_found_skip", "Warning: Theme folder not found, skipping deletion: {}").format(theme_dir))
            except FileNotFoundError:
                print(self._("print_warning_theme_folder_not_found_during_delete", "Warning: Theme folder not found during deletion (already removed?): {}").format(theme_dir))
            except PermissionError:
                self.show_message_safe("error", "permission_error_title", "error_permission_deleting_folder",
                                       title_key=self._("permission_error_title", "Permission Error"),
                                       message_key=self._("error_permission_deleting_folder", "Permission denied while deleting folder: {}\\n\\nMake sure the folder is not in use and you have necessary permissions.").format(selected_theme),
                                       args=[])
                self.update_status_safe(2, self._("status_failed_delete_theme_folder", "Failed to delete theme folder."), 40)
                self.show_message_safe("warning", "warning_partial_deletion_title", "warning_partial_deletion_message_permission",
                                       title_key=self._("warning_partial_deletion_title", "Partial Deletion"),
                                       message_key=self._("warning_partial_deletion_message_permission", "Could not delete theme folder '{}' due to permissions. Attempting to update ventoy.json.").format(selected_theme),
                                       args=[])
            except Exception as e:
                self.show_message_safe("error", "generic_error_title", "error_unexpected_deleting_theme_folder",
                                       title_key=self._("generic_error_title", "Error"),
                                       message_key=self._("error_unexpected_deleting_theme_folder", "An unexpected error occurred while deleting theme folder: {}").format(str(e)),
                                       args=[])
                self.update_status_safe(2, self._("status_failed_delete_theme_folder", "Failed to delete theme folder."), 40)
                self.show_message_safe("warning", "warning_partial_deletion_title", "warning_partial_deletion_message_unexpected",
                                       title_key=self._("warning_partial_deletion_title", "Partial Deletion"),
                                       message_key=self._("warning_partial_deletion_message_unexpected", "Could not delete theme folder '{}' due to an unexpected error. Attempting to update ventoy.json.").format(selected_theme),
                                       args=[])
            self.update_status_safe(2, self._("status_updating_config", "Updating config file..."), 60)
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                         config = json.load(f)
                except json.JSONDecodeError:
                    self.show_message_safe("error", "error_json_read_remove_title", "error_json_read_remove_message",
                                           title_key=self._("error_json_read_remove_title", "JSON Error"),
                                           message_key=self._("error_json_read_remove_message", "Failed to read ventoy.json on {drive}. File might be corrupted. Cannot update config.").format(drive=drive),
                                           args=[])
                    self.update_status_safe(2, self._("status_failed_update_config", "Failed to update config."), 100)
                    self.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_json_error",
                                           title_key=self._("dialog_deletion_status_title", "Deletion Status"),
                                           message_key=self._("dialog_deletion_status_json_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to a JSON error.").format(selected_theme),
                                           args=[])
                    self.root.after(0, self.load_existing_themes)
                    return

                except PermissionError:
                    self.show_message_safe("error", "permission_error_title", "error_permission_read_json_remove_message",
                                           title_key=self._("permission_error_title", "Permission Error"),
                                           message_key=self._("error_permission_read_json_remove_message", "Permission denied while reading ventoy.json on {drive}. Cannot update config.").format(drive=drive),
                                           args=[])
                    self.update_status_safe(2, self._("status_failed_update_config", "Failed to update config."), 100)
                    self.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_permission_error",
                                           title_key=self._("dialog_deletion_status_title", "Deletion Status"),
                                           message_key=self._("dialog_deletion_status_permission_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to a permission error.").format(selected_theme),
                                           args=[])
                    self.root.after(0, self.load_existing_themes)
                    return

                except Exception as e:
                    self.show_message_safe("error", "generic_error_title", "error_unexpected_read_json_remove_message",
                                           title_key=self._("generic_error_title", "Error"),
                                           message_key=self._("error_unexpected_read_json_remove_message", "An unexpected error occurred while reading ventoy.json: {}").format(str(e)),
                                           args=[])
                    self.update_status_safe(2, self._("status_failed_update_config", "Failed to update config."), 100)
                    self.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_unexpected_error",
                                           title_key=self._("dialog_deletion_status_title", "Deletion Status"),
                                           message_key=self._("dialog_deletion_status_unexpected_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to an unexpected error.").format(selected_theme),
                                           args=[])
                    self.root.after(0, self.load_existing_themes)
                    return


                if 'theme' in config:
                    normalized_theme_dir_on_drive = os.path.normpath(theme_dir)
                    def is_path_inside_deleted_theme_dir(ventoy_json_path):
                         if not ventoy_json_path or not isinstance(ventoy_json_path, str):
                             return False
                         try:
                             full_path_on_drive = os.path.normpath(os.path.join(drive, ventoy_json_path.lstrip('/')))
                             return full_path_on_drive.startswith(normalized_theme_dir_on_drive + os.sep) or full_path_on_drive == normalized_theme_dir_on_drive
                         except Exception:
                             return False
                    config['theme']['file'] = [
                         p for p in config['theme'].get('file', [])
                         if not is_path_inside_deleted_theme_dir(p)
                    ]
                    config['theme']['fonts'] = [
                         f for f in config['theme'].get('fonts', [])
                         if not is_path_inside_deleted_theme_dir(f)
                    ]
                    config['theme']['images'] = [
                         img for img in config['theme'].get('images', [])
                         if not is_path_inside_deleted_theme_dir(img)
                    ]
                    current_default_index = config['theme'].get('default_file', 0)
                    if current_default_index > 0:
                         if current_default_index > len(config['theme']['file']):
                              print(self._("print_resetting_default_theme_to_random", "Resetting default theme to Random."))
                              config['theme']['default_file'] = 0
                    try:
                        with open(json_path, 'w', encoding='utf-8') as f:
                             json.dump(config, f, indent=4)
                        print(self._("print_updated_json_successfully", "Updated ventoy.json successfully."))
                    except PermissionError:
                        self.show_message_safe("error", "permission_error_title", "error_permission_write_json_settings_message",
                                               title_key=self._("permission_error_title", "Permission Error"),
                                               message_key=self._("error_permission_write_json_settings_message", "Permission denied while writing to ventoy.json on {drive}. Make sure you have write access.").format(drive=drive),
                                               args=[])
                        self.update_status_safe(2, self._("status_failed_update_config", "Failed to update config."), 100)
                        return
                    except Exception as e:
                        self.show_message_safe("error", "generic_error_title", "error_unexpected_write_json_settings_message",
                                               title_key=self._("generic_error_title", "Error"),
                                               message_key=self._("error_unexpected_write_json_settings_message", "An unexpected error occurred while writing to ventoy.json: {}").format(str(e)),
                                               args=[])
                        self.update_status_safe(2, self._("status_failed_update_config", "Failed to update config."), 100)
                        return

                else:
                    self.show_message_safe("info", "dialog_deletion_status_title", "info_themes_deleted_json_not_found_message",
                                           title_key=self._("dialog_deletion_status_title", "Deletion Status"),
                                           message_key=self._("info_themes_deleted_json_not_found_message", "Themes deleted, but ventoy.json not found."))


            self.update_status_safe(2, self._("status_config_update_processed", "Config update processed."), 80)
            self.root.after(0, self.load_existing_themes)

            prefix_done = self._("status_theme_deletion_finished_prefix", "Theme '")
            suffix_done = self._("status_theme_deletion_finished_suffix", "' deletion process finished.")
            available_length_done = MAX_STATUS_LENGTH - len(prefix_done) - len(suffix_done)
            short_name_done = selected_theme if len(selected_theme) <= available_length_done else selected_theme[:available_length_done - 3] + "..."
            self.update_status_safe(2, f"{prefix_done}{short_name_done}{suffix_done}", 100)


        except Exception as e:
            self.show_message_safe("error", "generic_error_title", "error_during_theme_deletion_task",
                                   title_key=self._("generic_error_title", "Error"),
                                   message_key=self._("error_during_theme_deletion_task", "Error during theme deletion task: {}\\n{}").format(str(e), traceback.format_exc()),
                                   args=[])
            self.update_status_safe(2, self._("status_unexpected_error_deletion", "An unexpected error occurred during deletion."), 100)


        finally:
            self.set_buttons_state(tk.NORMAL)
            self.root.after(500, lambda: self.update_status_safe(2, self._("status_ready", "Status - READY"), 0))


    def remove_all_themes_task(self, drive):
        try:
            theme_dir = os.path.join(drive, "ventoy", "theme")
            json_file_path = os.path.join(drive, "ventoy", "ventoy.json")
            themes_to_delete = []
            if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
                try:
                    themes_to_delete = [item for item in os.listdir(theme_dir) if os.path.isdir(os.path.join(theme_dir, item))]
                except PermissionError:
                    self.show_message_safe("error", "permission_error_title", "error_permission_listing_theme_dir")
                    self.update_status_safe(2, self._("status_failed_list_themes_for_deletion", "Failed to list themes for deletion."), 100)
                except Exception as e:
                    self.show_message_safe("error", "generic_error_title", "error_listing_theme_directory", str(e))
                    self.update_status_safe(2, self._("status_failed_list_themes_for_deletion", "Failed to list themes for deletion."), 100)

            total = len(themes_to_delete)
            if total == 0:
                self.update_status_safe(2, self._("status_no_themes_found_in_directory", "No themes found in directory to delete."), 100)
            else:
                for idx, theme in enumerate(themes_to_delete, start=1):
                    theme_path = os.path.join(theme_dir, theme)
                    MAX_STATUS_LENGTH = 50
                    prefix = self._("status_deleting_short_prefix", "Deleting ")
                    suffix = self._("status_deleting_short_suffix", "...")
                    max_length = MAX_STATUS_LENGTH - len(prefix) - len(suffix)
                    short_name = theme if len(theme) <= max_length else theme[:max_length - 3] + "..."
                    self.update_status_safe(2, f"{prefix}{short_name}{suffix}", (idx / total) * 100)
                    try:
                        shutil.rmtree(theme_path)
                        print(self._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_path))
                    except FileNotFoundError:
                        print(self._("print_warning_theme_folder_not_found_during_delete", "Warning: Theme folder not found during deletion (already removed?): {}").format(theme_path))
                    except PermissionError:
                        self.show_message_safe("error", "permission_error_title", "error_permission_deleting_folder", theme)
                        continue

                    except Exception as e:
                        self.show_message_safe("error", "generic_error_title", "error_deleting_theme_file", theme, str(e))
                        continue
            if os.path.exists(json_file_path):
                try:
                    self.update_status_safe(2, self._("status_updating_config", "Updating config file..."), 80)
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                         config = json.load(f)
                    if 'theme' in config:
                         config['theme']['file'] = []
                         config['theme']['fonts'] = []
                         config['theme']['images'] = []
                         config['theme']['default_file'] = 0
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                         json.dump(config, f, indent=4)
                    print(self._("print_updated_json_successfully", "Updated ventoy.json successfully."))
                    self.update_status_safe(2, self._("status_config_update_processed", "Config update processed."), 90)

                except json.JSONDecodeError:
                    self.show_message_safe("error", "error_json_read_remove_title", "error_json_corrupted_message")
                    self.update_status_safe(2, self._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
                except PermissionError:
                    self.show_message_safe("error", "permission_error_title", "error_permission_writing_ventoy_json_remove")
                    self.update_status_safe(2, self._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
                except Exception as e:
                    self.show_message_safe("error", "generic_error_title", "error_failed_update_ventoy_json_remove", str(e))
                    self.update_status_safe(2, self._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
            elif total > 0:
                self.show_message_safe("info", "generic_info_title", "info_themes_deleted_json_not_found_message")
            self.update_status_safe(2, self._("status_all_themes_removed_config_updated", "All themes removed and config updated."), 100)
            self.root.after(0, self.load_existing_themes)

        except Exception as e:
            self.show_message_safe("error", "generic_error_title", "error_during_remove_all_themes_task", str(e), traceback.format_exc())
            self.update_status_safe(2, self._("status_unexpected_error_remove_all", "Unexpected error occurred."), 100)

        finally:
            self.set_buttons_state(tk.NORMAL)
            self.root.after(500, lambda: self.update_status_safe(2, self._("status_ready", "Status - READY"), 0))

    def start_remove_theme_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_message_safe("warning", "warning_busy_title", "warning_busy_message")
            return

        drive_display = self.drive_var.get()
        if not drive_display:
            self.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message")
            return

        selected = self.remove_theme_combo.get()
        if not selected or selected == self._("option_select_theme_to_delete", "Select a theme to delete"):
            self.show_message_safe("warning", "warning_select_drive_title", "warning_no_theme_selected_to_delete_message")
            return

        drive = extract_drive_letter(drive_display)
        theme_dir = os.path.join(drive, THEMES_DIR_NAME, selected)

        if not os.path.exists(theme_dir):
            self.show_message_safe("error", "generic_error_title", "error_theme_folder_not_found_message", theme_dir)
            self.root.after(0, self.load_existing_themes)
            return

        confirm = messagebox.askyesno(self._("dialog_confirm_delete_theme_title", "Confirm"),
                                     self._("dialog_confirm_delete_theme_message", "ARE YOU SURE YOU WANT TO DELETE THIS THEME?\\n\\nTHIS PROCESS CANNOT BE UNDONE!"))
        if not confirm:
            return

        self.current_drive = extract_drive_letter(drive_display)
        if not self.current_drive:
             self.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message")
             return

        self.reset_status()
        self.set_buttons_state(tk.DISABLED)
        self.worker_thread = threading.Thread(target=self.remove_theme_task, args=(self.current_drive, selected))
        self.worker_thread.start()

    def start_remove_all_themes_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_message_safe("warning", "warning_busy_title", "warning_busy_message")
            return

        drive_display = self.drive_var.get()
        if not drive_display:
            self.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message")
            return

        drive = extract_drive_letter(drive_display)
        theme_dir = os.path.join(drive, "ventoy", "theme")

        has_themes_on_disk = False
        if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
             try:
                 if any(os.path.isdir(os.path.join(theme_dir, item)) for item in os.listdir(theme_dir)):
                      has_themes_on_disk = True
             except PermissionError:
                  print(f"Permission denied checking theme directory: {theme_dir}")
             except Exception as e:
                  print(f"Error checking theme directory {theme_dir}: {e}")


        if not has_themes_on_disk:
             self.show_message_safe("info", "generic_info_title", "info_no_themes_to_delete_message")
             return

        confirm = messagebox.askyesno(self._("dialog_confirm_delete_all_themes_title", "Confirm"),
                                     self._("dialog_confirm_delete_all_themes_message", "ARE YOU SURE YOU WANT TO DELETE ALL THEMES?"))
        if not confirm:
            return

        self.current_drive = extract_drive_letter(drive_display)
        if not self.current_drive:
            self.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message")
            return

        self.reset_status()
        self.set_buttons_state(tk.DISABLED)
        self.worker_thread = threading.Thread(target=self.remove_all_themes_task, args=(self.current_drive,))
        self.worker_thread.start()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VentoyThemer(root)
    root.mainloop()
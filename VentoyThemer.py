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
import tkinter.font as tkFont
from tkinter import ttk
import os
import sys

import ventoy_support as support
import ventoy_archive as archive_service
import ventoy_theme_utils as theme_utils
import ventoy_config as ventoy_cfg
import ventoy_drive_service as drive_service
import ventoy_theme_jobs as theme_jobs
import ventoy_translation as translation_service
import ventoy_ui_helpers as ui_helpers
import ventoy_language_ui as language_ui
import ventoy_tab_ui as tab_ui
import ventoy_app_helpers as app_helpers
import ventoy_input_handlers as input_handlers
import ventoy_dnd as dnd

def get_drive_label(drive):
    return support.get_drive_label(drive)

def get_drive_size(drive):
    return support.get_drive_size(drive)

def get_drive_description(drive):
    return support.get_drive_description(drive)

def list_drives_display():
    return support.list_drives_display()


def extract_drive_letter(display_string):
    return support.extract_drive_root(display_string)


def pick_default_font(root):
    """Return a UI font tuple available on the current OS.

    Windows keeps the classic Courier New branding; Linux/macOS use the
    system sans-serif so the UI does not fall back to a bitmap-style mono.
    """
    if sys.platform.startswith("win"):
        preferred = ("Courier New", "Consolas", "Courier")
    elif sys.platform == "darwin":
        preferred = ("Helvetica Neue", "Helvetica", "Menlo", "Arial")
    else:
        preferred = ("DejaVu Sans", "Noto Sans", "Liberation Sans", "FreeSans", "DejaVu Sans Mono", "Helvetica")
    try:
        families = set(tkFont.families(root))
    except Exception:
        families = set()
    for name in preferred:
        if name in families:
            return (name, 10)
    return ("Courier", 10)


class VentoyThemer:
    def __init__(self, root):
        self.root = root
        self.all_translations, self._messages = translation_service.load_translations()
        detected = translation_service.detect_language(self.all_translations)
        if detected:
            self._messages = detected
        self.root.geometry("440x405" if sys.platform.startswith("win") else "480x405")
        root.minsize(440, 385)
        root.resizable(True, True)
        self._apply_window_icon()

        self.default_font = pick_default_font(root)
        self._drive_root_map = {}
        self.theme_sources_paths = []
        self.theme_display_names_from_json = []

        self.drive_var = tk.StringVar()
        self.default_theme_var = tk.StringVar()
        self.resolution_var = tk.StringVar()
        self.language_var = tk.StringVar()
        
        self.app_version = translation_service.load_version()

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
        self._fit_window_width()


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

    def _apply_window_icon(self):
        # .ico via iconbitmap is Windows-only; other platforms use
        # iconphoto with a PNG, which Tk 8.6+ can decode natively.
        try:
            if sys.platform.startswith("win"):
                icon_path = support.resource_path("VentoyThemer", "Logo.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(default=icon_path)
                else:
                    print(f"Warning: Icon file not found at {icon_path}")
            else:
                icon_path = support.resource_path("VentoyThemer", "Logo.png")
                if os.path.exists(icon_path):
                    self._icon_image = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(True, self._icon_image)
                else:
                    print(f"Warning: Icon file not found at {icon_path}")
        except Exception as e:
            print(f"Error setting window icon: {e}")

    def extract_drive_letter(self, display_string):
        root = self._drive_root_map.get(display_string)
        if root:
            return root
        return support.extract_drive_root(display_string)

    def _fit_window_width(self):
        """Widen the window so the widest translation fits.

        CJK/Armenian/etc. titles are much longer than English ones. After
        the new texts are applied, Tk's requested width already accounts
        for the notebook tab row, labels and the active theme — so the
        window is resized to that (never below 440), preserving the
        user-chosen height.
        """
        try:
            self.root.update_idletasks()
            # The notebook's requested width already accounts for the tab
            # row, labels and active theme, and stays fresh after text
            # changes (the root window's lags one resize behind).
            needed = self.notebook.winfo_reqwidth()
            height = self.root.winfo_height()
            if height <= 1:
                height = 405
            self.root.geometry(f"{max(440, needed)}x{height}")
        except Exception as e:
            print(f"Warning: could not fit window width: {e}")

    def _get_truncated_name(self, name, max_length=33, ellipsis="..."):
        return app_helpers._get_truncated_name(name, max_length=max_length, ellipsis=ellipsis)

    def on_default_theme_selected(self, event=None):
        pass

    def _show_overwrite_dialog_threaded(self, theme_name, result_queue):
        return app_helpers.show_overwrite_dialog_threaded(self, theme_name, result_queue)

    def define_styles(self):
        return ui_helpers.define_styles(self)

    def clear_zip_selection(self):
        return app_helpers.clear_zip_selection(self)

    def add_footer_links(self):
        return ui_helpers.add_footer_links(self)

    def reset_status(self):
        return app_helpers.reset_status(self)

    def update_status_safe(self, tab_index, message, progress=None):
        return app_helpers.update_status_safe(self, tab_index, message, progress)

    def show_message_safe(self, type, title_key, message_key, *args, **kwargs):
        return app_helpers.show_message_safe(self, type, title_key, message_key, *args, **kwargs)

    def set_buttons_state(self, state):
        return app_helpers.set_buttons_state(self, state)

    def extract_theme(self, archive_path, dest_path):
        return archive_service.extract_theme_archive(archive_path, dest_path, translate=self._)


    def find_theme_txt(self, root_dir):
        return theme_utils.find_theme_txt(root_dir)

    def find_pf2_fonts(self, root_dir):
        drive_display = self.drive_var.get()
        drive = self.extract_drive_letter(drive_display)
        if not drive:
            print(self._("error_extracting_drive_letter", "Error: Could not extract drive root from '{}'").format(drive_display))
            return set()
        return theme_utils.find_pf2_fonts(root_dir, drive)

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
        self.current_drive = self.extract_drive_letter(drive_display)
        if not self.current_drive:
            print(self._("error_extracting_drive_letter", "Error: Could not extract drive root from '{}'").format(drive_display))
            self.theme_display_names_from_json = []
            self.root.after(0, self.default_theme_combo.config, {'values': []})
            self.root.after(0, self.default_theme_var.set, "")
            self.root.after(0, self.remove_theme_combo.config, {'values': []})
            self.root.after(0, self.remove_theme_combo.set, "")
            self.resolution_var.set("")
            return
        state = drive_service.load_drive_theme_state(
            self.current_drive,
            self._("option_random_theme", "Random Theme"),
            self._("option_select_theme_to_delete", "Select a theme to delete"),
            self.resolution_combo['values'],
            support.THEMES_DIR_NAME,
            support.VENTOY_JSON_PATH,
        )

        self.theme_display_names_from_json = state["theme_display_names"]
        self.root.after(0, self.default_theme_combo.config, {'values': state["default_theme_values"]})
        self.root.after(0, self.default_theme_var.set, state["default_theme_value"])
        self.root.after(0, self.resolution_var.set, state["resolution_value"])
        self.root.after(0, self.remove_theme_combo.config, {'values': state["remove_theme_values"]})
        self.root.after(0, self.remove_theme_combo.set, self._("option_select_theme_to_delete", "Select a theme to delete"))
        
    def on_drive_selected(self, event=None):
        self.reset_status()
        self.load_existing_themes()

    def update_usb_drives(self):
        drives = support.list_available_drives()
        values = [drive.display for drive in drives]
        self._drive_root_map = {drive.display: drive.root for drive in drives}
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
        return ui_helpers.add_drive_selector(self, parent)

    def browse_zip(self):
        return input_handlers.browse_zip(self)


    def on_drop(self, event):
        return input_handlers.on_drop(self, event)

    def add_install_tab_widgets(self):
        return tab_ui.add_install_tab_widgets(self)

    def add_settings_tab_widgets(self):
        return tab_ui.add_settings_tab_widgets(self)

    def add_remove_tab_widgets(self):
        return tab_ui.add_remove_tab_widgets(self)

    def add_language_tab_widgets(self):
        return language_ui.add_language_tab_widgets(self)
        
    def on_language_selected(self, event=None):
        return language_ui.on_language_selected(self, event)

    def create_widgets(self):
        return tab_ui.create_widgets(self)

    def apply_theme_task(self, drive, theme_sources_paths):
        return theme_jobs.apply_theme_task(self, drive, theme_sources_paths)

    def start_apply_theme_thread(self):
        return theme_jobs.start_apply_theme_thread(self)

    def apply_settings_task(self, drive):
        return theme_jobs.apply_settings_task(self, drive)

    def start_apply_settings_thread(self):
         return theme_jobs.start_apply_settings_thread(self)

    def remove_theme_task(self, drive, selected_theme):
        return theme_jobs.remove_theme_task(self, drive, selected_theme)

    def remove_all_themes_task(self, drive):
        return theme_jobs.remove_all_themes_task(self, drive)

    def start_remove_theme_thread(self):
        return theme_jobs.start_remove_theme_thread(self)

    def start_remove_all_themes_thread(self):
         return theme_jobs.start_remove_all_themes_thread(self)

def main():
    root = dnd.TkinterDnD.Tk()
    app = VentoyThemer(root)
    root.mainloop()


if __name__ == "__main__":
    main()

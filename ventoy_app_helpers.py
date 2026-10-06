from __future__ import annotations

import queue

import tkinter as tk
from tkinter import messagebox


def _get_truncated_name(name, max_length=33, ellipsis="..."):
    if len(name) > max_length:
        return name[:max_length - len(ellipsis)] + ellipsis
    return name


def show_overwrite_dialog_threaded(app, theme_name, result_queue):
    dialog_title = app._("dialog_confirm_overwrite_title", "Confirm Overwrite")
    question = app._("dialog_confirm_overwrite_message", "Theme '{theme_name}' already exists.\
Do you want to overwrite it?\
\
All previous changes will be LOST!").format(theme_name=theme_name)
    overwrite_confirm = messagebox.askyesno(dialog_title, question)
    try:
        result_queue.put(overwrite_confirm, block=False)
    except queue.Full:
        print(f"Warning: Dialog result queue for '{theme_name}' was full.")


def clear_zip_selection(app):
    app.theme_listbox.delete(0, tk.END)
    app.theme_sources_paths = []


def reset_status(app):
    selected_tab = app.notebook.index(app.notebook.select())
    status_text = app._("status_ready", "Status - READY")

    if selected_tab == 0:
        app.status_bar_install.set(status_text)
        app.progress_value_install.set(0)
    elif selected_tab == 1:
        app.status_bar_settings.set(status_text)
        app.progress_value_settings.set(0)
    elif selected_tab == 2:
        app.status_bar_remove.set(status_text)
        app.progress_value_remove.set(0)


def update_status_safe(app, tab_index, message, progress=None):
    def update_gui():
        if tab_index == 0:
            app.status_bar_install.set(message)
            if progress is not None:
                app.progress_value_install.set(progress)
        elif tab_index == 1:
            app.status_bar_settings.set(message)
            if progress is not None:
                app.progress_value_settings.set(progress)
        elif tab_index == 2:
            app.status_bar_remove.set(message)
            if progress is not None:
                app.progress_value_remove.set(progress)

        app.root.update_idletasks()

    app.root.after(0, update_gui)


def show_message_safe(app, kind, title_key, message_key, *args, **kwargs):
    def show_gui_message():
        translated_title = app._(title_key, title_key)

        if message_key:
            translated_message = app._(message_key, message_key)
            try:
                formatted_message = translated_message.format(*args, **kwargs)
            except (IndexError, KeyError) as e:
                print(f"Formatting error for message key '{message_key}': {e}. Using raw translation.")
                formatted_message = translated_message
        else:
            formatted_message = args[0] if args else "Unknown Message"
            if (args or kwargs) and not message_key:
                print(f"Warning: show_message_safe called without message_key but with args/kwargs. Args: {args}, kwargs: {kwargs}")

        if kind == "info":
            messagebox.showinfo(translated_title, formatted_message)
        elif kind == "warning":
            messagebox.showwarning(translated_title, formatted_message)
        elif kind == "error":
            messagebox.showerror(translated_title, formatted_message)
        else:
            print(f"Error: show_message_safe called with unsupported type: {kind}")

    app.root.after(0, show_gui_message)


def set_buttons_state(app, state):
    def set_state():
        for btn in [app.apply_btn_install, app.browse_btn_install, app.clear_btn_install]:
            if btn and btn.winfo_exists():
                btn.config(state=state)

        for btn in [app.apply_btn_settings]:
            if btn and btn.winfo_exists():
                btn.config(state=state)

        for btn in [app.remove_btn, app.remove_all_btn]:
            if btn and btn.winfo_exists():
                btn.config(state=state)

        for combo in app.drive_combos:
            if combo and combo.winfo_exists():
                combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

        if app.default_theme_combo and app.default_theme_combo.winfo_exists():
            app.default_theme_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
        if app.resolution_combo and app.resolution_combo.winfo_exists():
            app.resolution_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

        if app.remove_theme_combo and app.remove_theme_combo.winfo_exists():
            app.remove_theme_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)

        if app.theme_listbox and app.theme_listbox.winfo_exists():
            app.theme_listbox.config(state=state)

    app.root.after(0, set_state)

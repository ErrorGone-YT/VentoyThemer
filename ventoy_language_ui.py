from __future__ import annotations

import tkinter as tk
from tkinter import ttk

OUTER_PADDING = 10
SECTION_SPACING = 5
TITLE_SPACING = 5
INNER_PADDING = 5
WIDGET_SPACING = 5


def add_language_tab_widgets(app):
    main_frame = ttk.Frame(app.language_tab)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))

    app.select_language_label = ttk.Label(main_frame, text=app._("select_language_label", "Select Language"), style="Courier.TLabel")
    app.select_language_label.pack(padx=INNER_PADDING, pady=(5, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((app.select_language_label, "select_language_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="x", padx=INNER_PADDING, pady=0)

    language_names = [lang.get("name", f"Unnamed Language {i+1}") for i, lang in enumerate(app.all_translations) if isinstance(lang, dict)]
    language_names.sort()

    app.language_combo = ttk.Combobox(
        content_frame,
        textvariable=app.language_var,
        values=language_names,
        state="readonly",
        style="Courier.TCombobox",
    )
    app.language_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)
    app.language_combo.bind("<<ComboboxSelected>>", app.on_language_selected)

    version_frame = ttk.Frame(app.language_tab)
    version_frame.place(relx=1.0, y=315, x=-10, anchor="e")

    format_string = app._("app_version_label", "Version: {}")
    try:
        version_text = format_string.format(app.app_version)
    except Exception as e:
        print(f"Error formatting version text: {e}")
        version_text = f"Formatting Error: {e}"

    app.app_version_label = ttk.Label(version_frame, text=version_text, style="Courier.TLabel")
    app.app_version_label.pack(padx=0, pady=0, anchor="w")
    app.translatable_widgets.append((app.app_version_label, "app_version_label"))


def on_language_selected(app, event=None):
    selected_name = app.language_var.get()

    selected_translation = None
    for lang_dict in app.all_translations:
        if isinstance(lang_dict, dict) and lang_dict.get("name") == selected_name:
            selected_translation = lang_dict
            break

    if selected_translation and selected_translation is not app._messages:
        app._messages = selected_translation
        print(f"Language changed to: {selected_name}")
        app.update_gui_language()
        app.on_drive_selected()
    elif not selected_translation and selected_name:
        print(f"Error: Selected language '{selected_name}' not found in translations list.")
        app.show_message_safe("error", "language_change_error_title", "language_change_error_message", selected_name=selected_name)

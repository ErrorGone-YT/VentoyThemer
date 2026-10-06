from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import ventoy_dnd as dnd

OUTER_PADDING = 10
SECTION_SPACING = 5
TITLE_SPACING = 5
INNER_PADDING = 5
WIDGET_SPACING = 5
BUTTON_GROUP_SPACING = 5


def add_install_tab_widgets(app):
    main_frame = ttk.Frame(app.install_tab)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
    if dnd.DND_AVAILABLE and dnd.DND_FILES is not None:
        main_frame.drop_target_register(dnd.DND_FILES)
        main_frame.dnd_bind("<<Drop>>", app.on_drop)

    title_label = ttk.Label(main_frame, text=app._("install_source_label", "Browse or Drag & Drop Theme Archives"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "install_source_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    list_scroll_frame = ttk.Frame(content_frame)
    list_scroll_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

    scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.theme_listbox = tk.Listbox(
        list_scroll_frame,
        height=5,
        selectmode=tk.MULTIPLE,
        width=35,
        yscrollcommand=scrollbar.set,
    )
    app.theme_listbox.pack(side=tk.LEFT, fill="both", expand=True)
    scrollbar.config(command=app.theme_listbox.yview)

    btn_frame = ttk.Frame(content_frame)
    btn_frame.pack(side="left", padx=(WIDGET_SPACING, 0), pady=0)

    app.browse_btn_install = ttk.Button(
        btn_frame,
        text=app._("browse_button", "Browse"),
        command=app.browse_zip,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.browse_btn_install.pack(pady=(0, BUTTON_GROUP_SPACING))
    app.translatable_widgets.append((app.browse_btn_install, "browse_button"))

    app.clear_btn_install = ttk.Button(
        btn_frame,
        text=app._("clear_button", "Clear"),
        command=app.clear_zip_selection,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.clear_btn_install.pack()
    app.translatable_widgets.append((app.clear_btn_install, "clear_button"))

    app.status_label_install = tk.Label(app.install_tab, textvariable=app.status_bar_install, anchor="w", font=app.default_font)
    app.status_label_install.place(x=5, y=220, width=425)

    app.progress_bar_install = ttk.Progressbar(app.install_tab, mode="determinate", variable=app.progress_value_install)
    app.progress_bar_install.place(x=5, y=250, width=425)

    app.apply_btn_install = ttk.Button(
        app.install_tab,
        text=app._("apply_themes_button", "Apply Themes"),
        command=app.start_apply_theme_thread,
        style="RoundedButton.TButton",
        width=15,
        takefocus=False,
    )
    app.apply_btn_install.place(x=136, y=282)
    app.translatable_widgets.append((app.apply_btn_install, "apply_themes_button"))


def add_settings_tab_widgets(app):
    default_theme_main_frame = ttk.Frame(app.settings_tab)
    default_theme_main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
    default_theme_title_label = ttk.Label(default_theme_main_frame, text=app._("select_default_theme_label", "Select Default Theme"), style="Courier.TLabel")
    default_theme_title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((default_theme_title_label, "select_default_theme_label"))

    default_theme_content_frame = ttk.Frame(default_theme_main_frame)
    default_theme_content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    combo_button_frame = ttk.Frame(default_theme_content_frame)
    combo_button_frame.pack(fill="x", padx=0, pady=0)

    app.default_theme_combo = ttk.Combobox(
        combo_button_frame,
        textvariable=app.default_theme_var,
        state="readonly",
        style="Courier.TCombobox",
    )
    app.default_theme_combo.pack(side="left", fill="x", expand=True, padx=0, pady=WIDGET_SPACING)
    app.default_theme_combo.bind("<<ComboboxSelected>>", app.on_default_theme_selected)

    resolution_main_frame = ttk.Frame(app.settings_tab)
    resolution_main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
    resolution_title_label = ttk.Label(resolution_main_frame, text=app._("choose_resolution_label", "Choose Standard Resolution"), style="Courier.TLabel")
    resolution_title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((resolution_title_label, "choose_resolution_label"))

    resolution_content_frame = ttk.Frame(resolution_main_frame)
    resolution_content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    app.resolution_combo = ttk.Combobox(
        resolution_content_frame,
        textvariable=app.resolution_var,
        state="readonly",
        style="Courier.TCombobox",
    )
    app.resolution_combo["values"] = [
        "max", "3840x2160", "2560x1440", "1920x1080", "1680x1050", "1600x900",
        "1440x900", "1280x1024", "1280x960", "1024x768", "800x600",
    ]
    app.resolution_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)

    app.apply_btn_settings = ttk.Button(
        app.settings_tab,
        text=app._("apply_settings_button", "Apply settings"),
        command=app.start_apply_settings_thread,
        style="RoundedButton.TButton",
        width=15,
        takefocus=False,
    )
    app.apply_btn_settings.place(x=136, y=282)
    app.translatable_widgets.append((app.apply_btn_settings, "apply_settings_button"))


def add_remove_tab_widgets(app):
    main_frame = ttk.Frame(app.remove_tab)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, SECTION_SPACING))
    title_label = ttk.Label(main_frame, text=app._("remove_theme_label", "Choose Theme to Delete"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "remove_theme_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)
    app.remove_theme_combo = ttk.Combobox(content_frame, state="readonly", style="Courier.TCombobox")
    app.remove_theme_combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)

    app.status_label_remove = tk.Label(app.remove_tab, textvariable=app.status_bar_remove, anchor="w", font=app.default_font)
    app.status_label_remove.place(x=5, y=220, width=425)

    app.progress_bar_remove = ttk.Progressbar(app.remove_tab, mode="determinate", variable=app.progress_value_remove)
    app.progress_bar_remove.place(x=5, y=250, width=425)

    app.remove_btn = ttk.Button(
        app.remove_tab,
        text=app._("remove_selected_button", "Remove Selected Theme"),
        command=app.start_remove_theme_thread,
        style="RoundedButton.TButton",
        width=21,
        takefocus=False,
    )
    app.remove_btn.place(x=230, y=282)
    app.translatable_widgets.append((app.remove_btn, "remove_selected_button"))

    app.remove_all_btn = ttk.Button(
        app.remove_tab,
        text=app._("remove_all_button", "Remove ALL THEMES"),
        command=app.start_remove_all_themes_thread,
        style="RoundedButton.TButton",
        width=21,
        takefocus=False,
    )
    app.remove_all_btn.place(x=10, y=282)
    app.translatable_widgets.append((app.remove_all_btn, "remove_all_button"))


def create_widgets(app):
    app.notebook = ttk.Notebook(app.root)
    app.notebook.pack(fill="both", expand=True, padx=0, pady=0)
    app.install_tab = ttk.Frame(app.notebook)
    app.settings_tab = ttk.Frame(app.notebook)
    app.remove_tab = ttk.Frame(app.notebook)
    app.language_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.install_tab, text=app._("install_tab_title", "Install Themes"))
    app.notebook.add(app.settings_tab, text=app._("settings_tab_title", "Themes Settings"))
    app.notebook.add(app.remove_tab, text=app._("remove_tab_title", "Remove Themes"))
    app.notebook.add(app.language_tab, text=app._("language_tab_title", "Language"))
    app.add_drive_selector(app.install_tab)
    app.add_drive_selector(app.settings_tab)
    app.add_drive_selector(app.remove_tab)
    app.add_install_tab_widgets()
    app.add_settings_tab_widgets()
    app.add_remove_tab_widgets()
    app.add_language_tab_widgets()
    app.add_footer_links()

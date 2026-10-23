from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import ventoy_dnd as dnd
from ventoy_ui_helpers import bordered_frame

OUTER_PADDING = 10
SECTION_SPACING = 5
TITLE_SPACING = 5
INNER_PADDING = 5
WIDGET_SPACING = 5
BUTTON_GROUP_SPACING = 5


def add_install_tab_widgets(app):
    main_frame = ttk.Frame(app.install_tab)
    main_frame.pack(fill="both", expand=True, padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
    if dnd.DND_AVAILABLE and dnd.DND_FILES is not None:
        main_frame.drop_target_register(dnd.DND_FILES)
        main_frame.dnd_bind("<<Drop>>", app.on_drop)

    title_label = ttk.Label(main_frame, text=app._("install_source_label", "Browse or Drag & Drop Theme Archives"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "install_source_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    list_scroll_frame = tk.Frame(
        content_frame, bg=app.ui_bg, highlightthickness=1, highlightbackground=app.border_color,
    )
    list_scroll_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

    scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox_kwargs = {}
    if app.modern_theme:
        listbox_kwargs = dict(
            bg="#ffffff", fg=app.ui_fg, selectbackground="#cde3f8", selectforeground=app.ui_fg,
            relief="flat", highlightthickness=0, activestyle="none",
        )
    app.theme_listbox = tk.Listbox(
        list_scroll_frame,
        height=5,
        selectmode=tk.MULTIPLE,
        width=35,
        yscrollcommand=scrollbar.set,
        **listbox_kwargs,
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

    app.apply_btn_install = ttk.Button(
        app.install_tab,
        text=app._("apply_themes_button", "Apply Themes"),
        command=app.start_apply_theme_thread,
        style="Accent.TButton",
        takefocus=False,
    )
    app.apply_btn_install.pack(side="bottom", pady=(WIDGET_SPACING, BUTTON_GROUP_SPACING + 4))
    app.translatable_widgets.append((app.apply_btn_install, "apply_themes_button"))

    progress_container = tk.Frame(app.install_tab, bg=app.ui_bg)
    progress_container.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, WIDGET_SPACING))

    app.progress_bar_install = ttk.Progressbar(progress_container, mode="determinate", variable=app.progress_value_install)
    app.progress_bar_install.pack(fill="x")

    app.status_label_install = tk.Label(
        app.install_tab, textvariable=app.status_bar_install, anchor="w", font=app.default_font,
        bg=app.ui_bg, fg=app.ui_fg, padx=6,
    )
    app.status_label_install.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, 2))



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

    default_theme_container = bordered_frame(app, combo_button_frame, side="left", fill="x", expand=True, pady=WIDGET_SPACING)
    app.default_theme_combo = ttk.Combobox(
        default_theme_container,
        textvariable=app.default_theme_var,
        state="readonly",
        style="Courier.TCombobox",
    )
    app.default_theme_combo.pack(side="left", fill="x", expand=True)
    app.default_theme_combo.bind("<<ComboboxSelected>>", app.on_default_theme_selected)

    resolution_main_frame = ttk.Frame(app.settings_tab)
    resolution_main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))
    resolution_title_label = ttk.Label(resolution_main_frame, text=app._("choose_resolution_label", "Choose Standard Resolution"), style="Courier.TLabel")
    resolution_title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((resolution_title_label, "choose_resolution_label"))

    resolution_content_frame = ttk.Frame(resolution_main_frame)
    resolution_content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    resolution_container = bordered_frame(app, resolution_content_frame, fill="x", pady=WIDGET_SPACING)
    app.resolution_combo = ttk.Combobox(
        resolution_container,
        textvariable=app.resolution_var,
        state="readonly",
        style="Courier.TCombobox",
    )
    app.resolution_combo["values"] = [
        "max", "3840x2160", "2560x1440", "1920x1080", "1680x1050", "1600x900",
        "1440x900", "1280x1024", "1280x960", "1024x768", "800x600",
    ]
    app.resolution_combo.pack(fill="x")

    app.apply_btn_settings = ttk.Button(
        app.settings_tab,
        text=app._("apply_settings_button", "Apply settings"),
        command=app.start_apply_settings_thread,
        style="Accent.TButton",
        takefocus=False,
    )
    app.apply_btn_settings.pack(side="bottom", pady=(WIDGET_SPACING, BUTTON_GROUP_SPACING + 4))
    app.translatable_widgets.append((app.apply_btn_settings, "apply_settings_button"))



def add_remove_tab_widgets(app):
    main_frame = ttk.Frame(app.remove_tab)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(SECTION_SPACING, SECTION_SPACING))
    title_label = ttk.Label(main_frame, text=app._("remove_theme_label", "Choose Theme to Delete"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "remove_theme_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)
    remove_theme_container = bordered_frame(app, content_frame, fill="x", pady=WIDGET_SPACING)
    app.remove_theme_combo = ttk.Combobox(remove_theme_container, state="readonly", style="Courier.TCombobox")
    app.remove_theme_combo.pack(fill="x")

    remove_btn_frame = ttk.Frame(app.remove_tab)
    remove_btn_frame.pack(side="bottom", pady=(WIDGET_SPACING, BUTTON_GROUP_SPACING + 4))

    app.remove_all_btn = ttk.Button(
        remove_btn_frame,
        text=app._("remove_all_button", "Remove ALL THEMES"),
        command=app.start_remove_all_themes_thread,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.remove_all_btn.pack(side="left", padx=(0, WIDGET_SPACING * 2))
    app.translatable_widgets.append((app.remove_all_btn, "remove_all_button"))

    app.remove_btn = ttk.Button(
        remove_btn_frame,
        text=app._("remove_selected_button", "Remove Selected Theme"),
        command=app.start_remove_theme_thread,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.remove_btn.pack(side="left")
    app.translatable_widgets.append((app.remove_btn, "remove_selected_button"))

    progress_container = tk.Frame(app.remove_tab, bg=app.ui_bg)
    progress_container.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, WIDGET_SPACING))

    app.progress_bar_remove = ttk.Progressbar(progress_container, mode="determinate", variable=app.progress_value_remove)
    app.progress_bar_remove.pack(fill="x")

    app.status_label_remove = tk.Label(
        app.remove_tab, textvariable=app.status_bar_remove, anchor="w", font=app.default_font,
        bg=app.ui_bg, fg=app.ui_fg, padx=6,
    )
    app.status_label_remove.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, 2))



def add_menuicons_tab_widgets(app):
    main_frame = ttk.Frame(app.menuicons_tab)
    main_frame.pack(fill="both", expand=True, padx=OUTER_PADDING, pady=(SECTION_SPACING, 0))

    title_label = ttk.Label(main_frame, text=app._("menuclass_files_label", "Image files on the drive"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "menuclass_files_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True, padx=INNER_PADDING, pady=0)

    btn_frame = ttk.Frame(content_frame)
    # Reserve the button column first: the expanding list must never push
    # it out of the window at narrow sizes. Grid with a uniform column
    # makes every control exactly as wide as the widest one.
    btn_frame.pack(side="right", padx=(WIDGET_SPACING, 0), pady=0)
    btn_frame.columnconfigure(0, weight=1, uniform="menuclass")

    list_scroll_frame = tk.Frame(
        content_frame, bg=app.ui_bg, highlightthickness=1, highlightbackground=app.border_color,
    )
    list_scroll_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

    scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app.style.configure("MenuClass.Treeview", rowheight=36, font=app.default_font)
    app.menuclass_tree = ttk.Treeview(
        list_scroll_frame,
        show="tree",
        selectmode=tk.EXTENDED,
        height=8,
        style="MenuClass.Treeview",
        yscrollcommand=scrollbar.set,
    )
    app.menuclass_tree.column("#0", width=430, stretch=True)
    app.menuclass_tree.pack(side=tk.LEFT, fill="both", expand=True)
    scrollbar.config(command=app.menuclass_tree.yview)

    app.menuclass_rescan_btn = ttk.Button(
        btn_frame,
        text=app._("menuclass_rescan_button", "Rescan"),
        command=app.start_scan_menu_class_thread,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.menuclass_rescan_btn.grid(row=0, column=0, sticky="ew", pady=(0, BUTTON_GROUP_SPACING))
    app.translatable_widgets.append((app.menuclass_rescan_btn, "menuclass_rescan_button"))

    app.menuclass_suggest_btn = ttk.Button(
        btn_frame,
        text=app._("menuclass_suggest_button", "Auto-Suggest"),
        command=app.menuclass_suggest,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.menuclass_suggest_btn.grid(row=1, column=0, sticky="ew", pady=(0, BUTTON_GROUP_SPACING))
    app.translatable_widgets.append((app.menuclass_suggest_btn, "menuclass_suggest_button"))

    class_entry_container = bordered_frame(app, btn_frame, grid_row=2, pady=(0, BUTTON_GROUP_SPACING))
    app.menuclass_class_var = tk.StringVar()
    # Editable combobox: the dropdown lists the classes the applied theme
    # can actually draw (its icons/ file names); anything else can still
    # be typed by hand for themes without icons.
    app.menuclass_class_entry = ttk.Combobox(
        class_entry_container,
        textvariable=app.menuclass_class_var,
        style="Courier.TCombobox",
    )
    app.menuclass_class_entry.pack(fill="x")
    app.menuclass_class_entry.bind("<Return>", lambda event: app.menuclass_set_class())

    app.menuclass_set_btn = ttk.Button(
        btn_frame,
        text=app._("menuclass_set_button", "Set Class"),
        command=app.menuclass_set_class,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.menuclass_set_btn.grid(row=3, column=0, sticky="ew", pady=(0, BUTTON_GROUP_SPACING))
    app.translatable_widgets.append((app.menuclass_set_btn, "menuclass_set_button"))

    app.menuclass_clear_btn = ttk.Button(
        btn_frame,
        text=app._("menuclass_clear_button", "Clear Class"),
        command=app.menuclass_clear_class,
        style="RoundedButton.TButton",
        takefocus=False,
    )
    app.menuclass_clear_btn.grid(row=4, column=0, sticky="ew")
    app.translatable_widgets.append((app.menuclass_clear_btn, "menuclass_clear_button"))

    app.apply_btn_menuclass = ttk.Button(
        app.menuicons_tab,
        text=app._("menuclass_apply_button", "Apply Menu Classes"),
        command=app.start_apply_menu_class_thread,
        style="Accent.TButton",
        takefocus=False,
    )
    app.apply_btn_menuclass.pack(side="bottom", pady=(WIDGET_SPACING, BUTTON_GROUP_SPACING + 4))
    app.translatable_widgets.append((app.apply_btn_menuclass, "menuclass_apply_button"))

    progress_container = tk.Frame(app.menuicons_tab, bg=app.ui_bg)
    progress_container.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, WIDGET_SPACING))

    app.progress_bar_menuicons = ttk.Progressbar(progress_container, mode="determinate", variable=app.progress_value_menuicons)
    app.progress_bar_menuicons.pack(fill="x")

    app.status_label_menuicons = tk.Label(
        app.menuicons_tab, textvariable=app.status_bar_menuicons, anchor="w", font=app.default_font,
        bg=app.ui_bg, fg=app.ui_fg, padx=6,
    )
    app.status_label_menuicons.pack(side="bottom", fill="x", padx=OUTER_PADDING, pady=(0, 2))


def create_widgets(app):
    app.notebook = ttk.Notebook(app.root)
    app.notebook.pack(fill="both", expand=True, padx=0, pady=0)
    # Tabs differ in content height; re-fit the window when switching.
    app.notebook.bind("<<NotebookTabChanged>>", lambda event: app._fit_window_width())
    app.install_tab = ttk.Frame(app.notebook)
    app.settings_tab = ttk.Frame(app.notebook)
    app.remove_tab = ttk.Frame(app.notebook)
    app.menuicons_tab = ttk.Frame(app.notebook)
    app.language_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.install_tab, text=app._("install_tab_title", "Install Themes"))
    app.notebook.add(app.settings_tab, text=app._("settings_tab_title", "Themes Settings"))
    app.notebook.add(app.remove_tab, text=app._("remove_tab_title", "Remove Themes"))
    app.notebook.add(app.menuicons_tab, text=app._("menuclass_tab_title", "Menu Icons"))
    app.notebook.add(app.language_tab, text=app._("language_tab_title", "Language"))
    app.add_drive_selector(app.install_tab)
    app.add_drive_selector(app.settings_tab)
    app.add_drive_selector(app.remove_tab)
    app.add_drive_selector(app.menuicons_tab)
    app.add_install_tab_widgets()
    app.add_settings_tab_widgets()
    app.add_remove_tab_widgets()
    app.add_menuicons_tab_widgets()
    app.add_language_tab_widgets()
    app.add_footer_links()

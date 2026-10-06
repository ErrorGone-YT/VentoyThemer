from __future__ import annotations

import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
import webbrowser

OUTER_PADDING = 10
INNER_PADDING = 5
TITLE_SPACING = 5
WIDGET_SPACING = 5


def define_styles(app):
    app.root.option_add("*Font", app.default_font)
    app.root.option_add("*Listbox*Font", app.default_font)
    app.root.option_add("*TLabel*Font", app.default_font)
    app.root.option_add("*TButton*Font", app.default_font)
    app.root.option_add("*TCombobox*Font", app.default_font)
    app.root.option_add("*TCombobox*Listbox*Font", app.default_font)
    app.root.option_add("*TLabelframe*Font", app.default_font)
    app.root.option_add("*TEntry*Font", app.default_font)

    app.style.configure("TLabel", font=app.default_font)
    app.style.configure("Courier.TLabel", font=app.default_font)

    app.style.configure("TButton", font=app.default_font)
    app.style.configure(
        "RoundedButton.TButton",
        relief="flat",
        background=app.root.cget("background"),
        foreground="#000000",
        padding=10,
        borderwidth=0,
        font=app.default_font,
        takefocus=False,
    )
    app.style.map(
        "RoundedButton.TButton",
        background=[("active", "#e6f2ff"), ("!active", app.root.cget("background"))],
        foreground=[("active", "#000000")],
    )

    app.style.configure("TCombobox", font=app.default_font)
    app.style.configure("Courier.TCombobox", font=app.default_font)

    app.style.configure("TLabelframe", font=app.default_font)
    app.style.configure("Courier.TLabelframe", font=app.default_font)


def add_footer_links(app):
    footer = tk.Frame(app.root)
    footer.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    link_font = tkFont.Font(family=app.default_font[0], size=10, underline=True)

    left_frame = tk.Frame(footer)
    center_frame = tk.Frame(footer)
    right_frame = tk.Frame(footer)

    left_frame.pack(side=tk.LEFT, expand=False, anchor="w", padx=10)
    right_frame.pack(side=tk.RIGHT, expand=False, anchor="e", padx=10)
    center_frame.pack(side=tk.LEFT, expand=True, anchor="center")

    link1 = tk.Label(left_frame, text=app._("donate_link_text", "Donate"), fg="blue", cursor="hand2", font=link_font)
    link1.pack()
    link1.bind("<Button-1>", lambda e: webbrowser.open("https://errorgone-yt.github.io/Donat"))
    app.translatable_widgets.append((link1, "donate_link_text"))

    link2 = tk.Label(center_frame, text=app._("download_themes_link_text", "Download New Theme"), fg="blue", cursor="hand2", font=link_font)
    link2.pack()
    link2.bind("<Button-1>", lambda e: webbrowser.open("https://www.gnome-look.org/browse?cat=109&ord=latest"))
    app.translatable_widgets.append((link2, "download_themes_link_text"))

    link3 = tk.Label(right_frame, text=app._("ventoy_themer_link_text", "Project Page"), fg="blue", cursor="hand2", font=link_font)
    link3.pack()
    link3.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/ErrorGone-YT/VentoyThemer"))
    app.translatable_widgets.append((link3, "ventoy_themer_link_text"))


def add_drive_selector(app, parent):
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(OUTER_PADDING, 0))

    title_label = ttk.Label(main_frame, text=app._("device_label", "Device"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "device_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="x", padx=INNER_PADDING, pady=0)

    combo = ttk.Combobox(
        content_frame,
        textvariable=app.drive_var,
        postcommand=app.update_usb_drives,
        state="readonly",
        style="Courier.TCombobox",
    )
    combo.pack(fill="x", padx=0, pady=WIDGET_SPACING)
    combo.bind("<<ComboboxSelected>>", app.on_drive_selected)

    if not hasattr(app, "drive_combos"):
        app.drive_combos = []
    app.drive_combos.append(combo)

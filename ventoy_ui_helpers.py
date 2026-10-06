from __future__ import annotations

import os
import sys

import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
import webbrowser

OUTER_PADDING = 10
INNER_PADDING = 5
TITLE_SPACING = 5
WIDGET_SPACING = 5


def _import_sv_ttk():
    """Import sv_ttk, falling back to the copy vendored in ./vendor.

    The pip package is preferred when present; the vendored copy keeps the
    modern look working for plain source runs and PyInstaller builds where
    the dependency was never installed.
    """
    try:
        import sv_ttk

        return sv_ttk
    except Exception:
        pass
    vendor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
    if os.path.isdir(vendor_dir) and vendor_dir not in sys.path:
        sys.path.insert(0, vendor_dir)
    try:
        import sv_ttk

        return sv_ttk
    except Exception:
        return None


def _select_ttk_theme(app):
    """Pick the nicest ttk theme per OS.

    Windows keeps the native vista theme; Linux/macOS use the modern
    Sun Valley theme (vendored, so always available), falling back to
    clam/alt. Sets app.modern_theme so the UI can adapt decorations
    (image-based themes ignore plain color configuration).
    """
    app.modern_theme = False
    if sys.platform.startswith("win"):
        return
    sv_ttk = _import_sv_ttk()
    if sv_ttk is not None:
        try:
            sv_ttk.set_theme("light")
            app.modern_theme = True
            _boost_sv_ttk_hover(app)
            return
        except Exception:
            pass
    style = app.style
    if sys.platform.startswith("linux"):
        for theme in ("clam", "alt"):
            try:
                if theme in style.theme_names():
                    style.theme_use(theme)
                    return
            except tk.TclError:
                continue


# sv-ttk's stock hover sprites differ from the resting ones by a single
# barely-visible shade; these multipliers darken them in place so pointer
# feedback is actually noticeable.
_HOVER_SPRITE_SCALES = {
    "button-hover": 0.90,
    "button-accent-hover": 0.86,
    "tab-hover": 0.92,
}


def _boost_sv_ttk_hover(app):
    for sprite, scale in _HOVER_SPRITE_SCALES.items():
        try:
            image = app.root.tk.eval(f"set ::ttk::theme::sv_light::I({sprite})")
            # `image data` returns one space-separated color string per row,
            # with empty entries for transparent pixels.
            recolored = [
                " ".join(_scale_hex(px, scale) if px.startswith("#") else px for px in str(row).split(" "))
                for row in app.root.tk.call(image, "data")
            ]
            app.root.tk.call(image, "put", recolored)
        except Exception:
            continue


def _scale_hex(pixel, scale):
    digits = pixel[1:]
    alpha_suffix = ""
    if len(digits) == 8:
        alpha_suffix = digits[6:]
        digits = digits[:6]
    channels = [max(0, min(255, round(int(digits[i:i + 2], 16) * scale))) for i in (0, 2, 4)]
    return "#" + "".join(f"{c:02x}" for c in channels) + alpha_suffix


def _theme_palette(app):
    """Background/foreground for classic tk widgets, matching the ttk theme.

    sv-ttk's light palette is fixed; native/other themes are queried from
    the style so classic widgets do not sit on mismatched gray patches.
    """
    if app.modern_theme:
        return "#fafafa", "#1a1a1a"
    bg = app.root.cget("background")
    try:
        bg = app.style.lookup("TLabel", "background") or bg
    except tk.TclError:
        pass
    try:
        fg = app.style.lookup("TLabel", "foreground") or "#000000"
    except tk.TclError:
        fg = "#000000"
    return bg, fg


def define_styles(app):
    _select_ttk_theme(app)
    app.ui_bg, app.ui_fg = _theme_palette(app)
    # Image-based modern themes draw flat widgets; give input elements a
    # 1px border so they read as fields. On Windows (native theme) the
    # "border" uses the window background color and stays invisible.
    if sys.platform.startswith("win"):
        app.border_color = app.ui_bg
    else:
        app.border_color = "#b4b4b4" if app.modern_theme else "#a6a6a6"
    app.root.configure(bg=app.ui_bg)
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

    app.style.configure("TCombobox", font=app.default_font)
    app.style.configure("Courier.TCombobox", font=app.default_font)

    app.style.configure("TLabelframe", font=app.default_font)
    app.style.configure("Courier.TLabelframe", font=app.default_font)

    app.style.configure("RoundedButton.TButton", font=app.default_font)
    app.style.configure("Accent.TButton", font=app.default_font)
    if sys.platform.startswith("win"):
        # Flat custom look; the vista theme ignores the background anyway,
        # so buttons keep their native borders.
        app.style.configure(
            "RoundedButton.TButton",
            relief="flat",
            background=app.root.cget("background"),
            foreground="#000000",
            padding=10,
            borderwidth=0,
            takefocus=False,
        )
        app.style.map(
            "RoundedButton.TButton",
            background=[("active", "#e6f2ff"), ("!active", app.root.cget("background"))],
            foreground=[("active", "#000000")],
        )
    # On Linux/macOS the style stays unconfigured apart from the font, so
    # themed buttons (clam/aqua) keep their native borders and hover look.


def add_footer_links(app):
    footer = tk.Frame(app.root, bg=app.ui_bg)
    footer.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    link_font = tkFont.Font(family=app.default_font[0], size=10, underline=True)

    left_frame = tk.Frame(footer, bg=app.ui_bg)
    center_frame = tk.Frame(footer, bg=app.ui_bg)
    right_frame = tk.Frame(footer, bg=app.ui_bg)

    left_frame.pack(side=tk.LEFT, expand=False, anchor="w", padx=10)
    right_frame.pack(side=tk.RIGHT, expand=False, anchor="e", padx=10)
    center_frame.pack(side=tk.LEFT, expand=True, anchor="center")

    link1 = tk.Label(left_frame, text=app._("donate_link_text", "Donate"), fg="blue", bg=app.ui_bg, cursor="hand2", font=link_font)
    link1.pack()
    link1.bind("<Button-1>", lambda e: webbrowser.open("https://errorgone-yt.github.io/Donat"))
    app.translatable_widgets.append((link1, "donate_link_text"))

    link2 = tk.Label(center_frame, text=app._("download_themes_link_text", "Download New Theme"), fg="blue", bg=app.ui_bg, cursor="hand2", font=link_font)
    link2.pack()
    link2.bind("<Button-1>", lambda e: webbrowser.open("https://www.gnome-look.org/browse?cat=109&ord=latest"))
    app.translatable_widgets.append((link2, "download_themes_link_text"))

    link3 = tk.Label(right_frame, text=app._("ventoy_themer_link_text", "Project Page"), fg="blue", bg=app.ui_bg, cursor="hand2", font=link_font)
    link3.pack()
    link3.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/ErrorGone-YT/VentoyThemer"))
    app.translatable_widgets.append((link3, "ventoy_themer_link_text"))


def bordered_frame(app, parent, **pack_kwargs):
    """A 1px-bordered container for input elements (combos, lists, bars)."""
    frame = tk.Frame(parent, bg=app.ui_bg, highlightthickness=1, highlightbackground=app.border_color)
    frame.pack(**pack_kwargs)
    return frame


def add_drive_selector(app, parent):
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="x", padx=OUTER_PADDING, pady=(OUTER_PADDING, 0))

    title_label = ttk.Label(main_frame, text=app._("device_label", "Device"), style="Courier.TLabel")
    title_label.pack(padx=INNER_PADDING, pady=(0, TITLE_SPACING), anchor="w")
    app.translatable_widgets.append((title_label, "device_label"))

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="x", padx=INNER_PADDING, pady=0)

    combo_container = bordered_frame(app, content_frame, fill="x", pady=WIDGET_SPACING)
    combo = ttk.Combobox(
        combo_container,
        textvariable=app.drive_var,
        postcommand=app.update_usb_drives,
        state="readonly",
        style="Courier.TCombobox",
    )
    combo.pack(fill="x")
    combo.bind("<<ComboboxSelected>>", app.on_drive_selected)

    if not hasattr(app, "drive_combos"):
        app.drive_combos = []
    app.drive_combos.append(combo)

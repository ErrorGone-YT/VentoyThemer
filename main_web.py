"""VentoyThemer — web UI entry point (pywebview).

The Tkinter interface stays available via the classic entry; this one
renders the same functionality in an HTML/CSS/JS interface that looks
identical on Windows (WebView2), Linux (WebKitGTK) and macOS (WKWebView).
"""
from __future__ import annotations

import os
import sys

if sys.platform.startswith("linux"):
    # WebKitGTK renders a black window with GPU compositing on many
    # drivers (WSLg, NVIDIA, older Mesa); software rendering is reliable
    # everywhere. Users can override by setting the vars themselves.
    os.environ.setdefault("WEBKIT_DISABLE_COMPOSITING_MODE", "1")
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")

import webview

# PyInstaller: data files live in the bundle dir (sys._MEIPASS);
# from source they live next to this file.
if getattr(sys, "frozen", False):
    ROOT_DIR = sys._MEIPASS
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
from web_backend import Api, attach_window  # noqa: E402


def main():
    api = Api()
    window = webview.create_window(
        "VentoyThemer",
        os.path.join(ROOT_DIR, "webui", "index.html"),
        js_api=api,
        width=1280,
        height=760,
        min_size=(1000, 600),
        background_color="#16181d",
    )
    attach_window(window)
    window.events.loaded += api.register_dom_hooks
    webview.start(debug=bool(os.environ.get("VT_WEB_DEBUG")))


if __name__ == "__main__":
    sys.exit(main())

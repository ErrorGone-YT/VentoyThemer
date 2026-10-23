from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import ventoy_menu_class as menu_class_service


SUPPORTED_ARCHIVE_EXTENSIONS = (
    ".zip", ".tar", ".tar.gz", ".tgz", ".xz", ".rar", ".7z", ".zipx", ".tar.bz2", ".tar.lz4", ".tar.zst"
)


def browse_zip(app):
    paths = filedialog.askopenfilenames(
        title=app._("dialog_select_theme_archives_title", "Select Theme Archive(s)"),
        filetypes=[("Theme Archives", "*.zip *.tar *.gz *.tgz *.xz *.rar *.7z *.zipx *.tar.bz2 *.tar.lz4 *.tar.zst"), ("All files", "*.*")],
    )
    for path in paths:
        if path and os.path.isfile(path):
            if path not in app.theme_sources_paths:
                app.theme_sources_paths.append(path)
                file_name = os.path.basename(path)
                display_name = app._get_truncated_name(file_name)
                app.theme_listbox.insert("end", display_name)
            else:
                print(app._("print_skipping_already_added_file", "Warning: Skipping already added file: {}").format(path))
        elif path:
            print(app._("print_skipped_non_file_selection", "Warning: Skipping non-file selection: {}").format(path))


def on_drop(app, event):
    paths = app.root.tk.splitlist(event.data)
    total_processed_count = 0

    for path in paths:
        path = os.path.normpath(path)
        processed_count_in_this_item = 0
        if os.path.isdir(path):
            print(app._("print_dropped_directory", "Dropped directory: {}").format(path))

            potential_sources_to_add = []
            found_archives_in_root = []
            try:
                if os.path.exists(path):
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isfile(item_path) and item.lower().endswith(SUPPORTED_ARCHIVE_EXTENSIONS):
                            found_archives_in_root.append(item_path)
            except PermissionError:
                print(app._("print_warning_permission_denied_list_dir", "Warning: Permission denied listing directory: {}").format(path))
                app.show_message_safe("warning", "warning_permission_denied_title", "warning_permission_denied_message", path)
                continue
            except Exception as e:
                print(f"Error listing directory {path}: {e}")
                app.show_message_safe("error", "error_listing_directory_title", "error_listing_directory_message", path, e)
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
                                if app.find_theme_txt(item_path):
                                    found_theme_subfolders.append(item_path)
                except PermissionError:
                    print(app._("print_warning_permission_denied_list_dir", "Warning: Permission denied listing directory: {}").format(path))
                    app.show_message_safe("warning", "warning_permission_denied_title", "warning_permission_denied_message", path)
                    continue
                except Exception as e:
                    print(f"Error checking subdirectories in {path}: {e}")
                    app.show_message_safe("error", "error_listing_directory_title", "error_listing_directory_message", path, e)
                    continue

                if found_theme_subfolders:
                    print("Detected folder containing theme folders:", path)
                    potential_sources_to_add.extend(found_theme_subfolders)
                    directory_content_type = "theme_folders_in_subdirs"
                else:
                    if app.find_theme_txt(path):
                        print("Detected dropped folder is a single theme folder:", path)
                        potential_sources_to_add.append(path)
                        directory_content_type = "single_theme_folder"
                    else:
                        print(app._("warning_skipping_directory_content_warning", "Skipping directory '{}' as it does not contain supported theme archives or theme folders.").format(os.path.basename(path)))
                        app.root.after(0, messagebox.showwarning, app._("warning_skipping_directory_title", "Skipping Directory"), app._("warning_skipping_directory_content_warning", "Skipping directory '{}' as it does not contain supported theme archives or theme folders.").format(os.path.basename(path)))
                        directory_content_type = "skipped_no_content"

            if potential_sources_to_add:
                for source_path in potential_sources_to_add:
                    if source_path not in app.theme_sources_paths:
                        app.theme_sources_paths.append(source_path)
                        if os.path.isfile(source_path):
                            file_name = os.path.basename(source_path)
                            display_name = app._get_truncated_name(file_name)
                            app.root.after(0, app.theme_listbox.insert, "end", display_name)
                            print("Added archive source from directory:", source_path)
                        elif os.path.isdir(source_path):
                            folder_name = os.path.basename(source_path)
                            display_name = app._get_truncated_name(folder_name)
                            folder_prefix = app._("listbox_folder_prefix", "[FOLDER]")
                            app.root.after(0, app.theme_listbox.insert, "end", f"{folder_prefix} {display_name}")
                            print("Added theme folder source from directory:", source_path)
                        processed_count_in_this_item += 1
                    else:
                        print("Warning: Skipping already added source from directory:", source_path)

            if directory_content_type != "skipped_no_content":
                if processed_count_in_this_item > 0:
                    if directory_content_type == "archives_in_root":
                        msg_key = "status_added_dropped_archives_from_folder"
                        default_msg = "Added {} archive(s) from dropped folder '{}'."
                        app.update_status_safe(0, app._(msg_key, default_msg).format(processed_count_in_this_item, os.path.basename(path)), 0)
                    elif directory_content_type == "theme_folders_in_subdirs":
                        msg_key = "status_added_dropped_theme_folders_from_folder"
                        default_msg = "Added {} theme folder(s) from dropped folder '{}'."
                        app.update_status_safe(0, app._(msg_key, default_msg).format(processed_count_in_this_item, os.path.basename(path)), 0)
                    elif directory_content_type == "single_theme_folder":
                        msg_key = "status_added_dropped_single_theme_folder"
                        default_msg = "Added theme folder '{}'."
                        app.update_status_safe(0, app._(msg_key, default_msg).format(os.path.basename(path)), 0)

        elif os.path.isfile(path):
            if path.lower().endswith(SUPPORTED_ARCHIVE_EXTENSIONS):
                if path not in app.theme_sources_paths:
                    app.theme_sources_paths.append(path)
                    file_name = os.path.basename(path)
                    display_name = app._get_truncated_name(file_name)
                    app.root.after(0, app.theme_listbox.insert, "end", display_name)
                    print(app._("print_added_theme_archive_source", "Added theme archive source: {}").format(path))
                    processed_count_in_this_item += 1
                else:
                    print(app._("print_skipping_already_added_file", "Warning: Skipping already added file: {}").format(path))
            else:
                print(app._("print_skipping_unsupported_file_extension", "Warning: Skipping unsupported file extension: {}").format(os.path.basename(path)))
        else:
            print(app._("print_skipping_unsupported_dropped_item", "Warning: Skipping unsupported dropped item: {}").format(path))

        total_processed_count += processed_count_in_this_item

    if total_processed_count > 0:
        app.update_status_safe(0, app._("status_added_dropped_items_total", "Added {} item(s).").format(total_processed_count), 0)
    elif total_processed_count == 0 and paths:
        app.update_status_safe(0, app._("status_no_supported_dropped_items", "No supported items found in dropped items."), 0)


def menuclass_on_scan_finished(app, files, base_classes, mode, rules, available_classes, icons_dir):
    """Main-thread callback: scan_menu_class_task finished successfully."""
    app.menuclass_files = files
    app.menuclass_base = base_classes
    app.menuclass_mode = mode
    app.menuclass_rules = rules
    app.menuclass_available = available_classes
    if getattr(app, "menuclass_icons_dir", None) != icons_dir:
        app.menuclass_icon_cache = {}
    app.menuclass_icons_dir = icons_dir
    app.menuclass_overrides = {}
    if getattr(app, "menuclass_class_entry", None) is not None and app.menuclass_class_entry.winfo_exists():
        app.menuclass_class_entry["values"] = tuple(available_classes)
    menuclass_refresh_list(app)


def menuclass_display_class(app, path):
    override = app.menuclass_overrides.get(path)
    if override is None:
        return app.menuclass_base.get(path, menu_class_service.built_in_class(path))
    if override == "":
        return menu_class_service.built_in_class(path)
    return override


def menuclass_icon_for(app, cls):
    """PhotoImage of the theme icon for this class, or None.

    Images are cached per class and kept referenced on the app, or Tk
    garbage-collects them and rows render blank.
    """
    cache = getattr(app, "menuclass_icon_cache", None)
    icons_dir = getattr(app, "menuclass_icons_dir", None)
    if cache is None or not icons_dir or cls in cache:
        return cache.get(cls) if cache else None
    image = None
    try:
        full = os.path.join(icons_dir, cls + ".png")
        if os.path.isfile(full):
            photo = tk.PhotoImage(file=full)
            shrink_x = max(1, -(-photo.width() // 32))
            shrink_y = max(1, -(-photo.height() // 32))
            if shrink_x > 1 or shrink_y > 1:
                photo = photo.subsample(shrink_x, shrink_y)
            image = photo
    except Exception as e:
        print(f"Could not load icon for class '{cls}': {e}")
        image = None
    cache[cls] = image
    return image


def menuclass_refresh_list(app):
    tree = getattr(app, "menuclass_tree", None)
    if not tree or not tree.winfo_exists():
        return
    tree.delete(*tree.get_children())
    for path in app.menuclass_files:
        cls = menuclass_display_class(app, path)
        opts = {"text": f"{path}  ->  {cls}"}
        image = menuclass_icon_for(app, cls)
        if image is not None:
            opts["image"] = image
        tree.insert("", "end", iid=path, **opts)


def menuclass_selected_paths(app):
    tree = getattr(app, "menuclass_tree", None)
    if not tree or not tree.winfo_exists():
        return []
    return list(tree.selection())


def menuclass_set_class(app):
    selected = menuclass_selected_paths(app)
    class_value = app.menuclass_class_var.get().strip()
    if not selected or not class_value:
        app.show_message_safe("warning", "generic_warning_title", "menuclass_warning_no_selection")
        return
    for path in selected:
        app.menuclass_overrides[path] = class_value
    menuclass_refresh_list(app)


def menuclass_clear_class(app):
    selected = menuclass_selected_paths(app)
    if not selected:
        app.show_message_safe("warning", "generic_warning_title", "menuclass_warning_no_selection")
        return
    for path in selected:
        app.menuclass_overrides[path] = ""
    menuclass_refresh_list(app)


def menuclass_suggest(app):
    available = getattr(app, "menuclass_available", [])
    suggested = 0
    for path in app.menuclass_files:
        if path in app.menuclass_overrides:
            continue
        guess = menu_class_service.suggest_class(path)
        # Only suggest classes the active theme can actually draw.
        if guess and (not available or guess in available):
            app.menuclass_overrides[path] = guess
            suggested += 1
    if suggested:
        app.update_status_safe(3, app._("menuclass_status_suggested", "Auto-suggested {} class(es).").format(suggested), 0)
    else:
        app.update_status_safe(3, app._("menuclass_status_ready", "Status - READY"), 0)
    menuclass_refresh_list(app)


def menuclass_snapshot(app):
    """Snapshot UI state for the apply worker, or None with a warning shown."""
    if not app.menuclass_files:
        app.show_message_safe("warning", "warning_select_drive_title", "menuclass_warning_no_files")
        return None
    overrides = {path: value for path, value in app.menuclass_overrides.items() if path in app.menuclass_files}
    return {
        "files": list(app.menuclass_files),
        "overrides": overrides,
        "rules": list(app.menuclass_rules),
    }

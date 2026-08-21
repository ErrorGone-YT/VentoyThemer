from __future__ import annotations

import os
from tkinter import filedialog, messagebox


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

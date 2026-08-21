from __future__ import annotations

import json
import os
import queue
import shutil
import threading
import traceback

import tkinter as tk
from tkinter import messagebox

import ventoy_config as ventoy_cfg
import ventoy_support as support


def _delete_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def apply_theme_task(app, drive, theme_sources_paths):
    try:
        total = len(theme_sources_paths)
        if total == 0:
            app.update_status_safe(0, app._("status_no_theme_items_warning_message", "No theme items to process."), 100)
            return

        all_paths = set()
        all_fonts = set()
        for i, source_path in enumerate(theme_sources_paths):
            processed_count = i + 1
            if not os.path.exists(source_path):
                app.update_status_safe(0, app._("status_skipped_missing_source", "Skipping missing source: {}").format(os.path.basename(source_path)), 100 * i / total)
                app.show_message_safe("warning", "warning_source_not_found_title", "warning_source_not_found_message",
                                      title_key=app._("warning_source_not_found_title", "Source Not Found"),
                                      message_key=app._("warning_source_not_found_message", "Theme source not found: {}. Skipping.").format(os.path.basename(source_path)))
                continue

            theme_name = os.path.splitext(os.path.basename(source_path))[0] if os.path.isfile(source_path) else os.path.basename(source_path)
            theme_dir = os.path.join(drive, support.THEMES_DIR_NAME)
            theme_dir = os.path.join(theme_dir, theme_name)

            should_process = True
            if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
                app.update_status_safe(0, app._("status_confirming_overwrite", "Confirming overwrite for {}...").format(theme_name), 100 * (i / total))
                result_queue = queue.Queue(maxsize=1)
                app.root.after(0, app._show_overwrite_dialog_threaded, theme_name, result_queue)
                try:
                    overwrite_confirmed = result_queue.get(block=True)
                    print(f"Received confirmation for '{theme_name}': {overwrite_confirmed}")
                    if not overwrite_confirmed:
                        should_process = False
                except Exception as e:
                    print(f"Error while waiting for overwrite confirmation for '{theme_name}': {e}")
                    app.show_message_safe("error", "error_task_title", "error_task_message",
                                           title_key=app._("error_task_title", "Task Error"),
                                           message_key=app._("error_task_message", "An unexpected error occurred during task: {}\\n{}").format(f"Failed to get confirmation for theme '{theme_name}'. Skipping this theme.", ""),
                                           args=[])
                    should_process = False

            if should_process:
                try:
                    if os.path.isdir(theme_dir) and os.path.isdir(source_path):
                        print(f"Overwriting existing theme directory: {theme_dir}")
                        _delete_folder(theme_dir)
                        print(app._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_dir))

                    if os.path.isfile(source_path):
                        os.makedirs(theme_dir, exist_ok=True)
                        app.update_status_safe(0, app._("status_extracting", "Extracting {}...").format(theme_name), 100 * (i / total))
                        app.extract_theme(source_path, theme_dir)
                    elif os.path.isdir(source_path):
                        app.update_status_safe(0, app._("status_copying", "Copying theme folder {}...").format(theme_name), 100 * (i / total))
                        shutil.copytree(source_path, theme_dir)
                        print(app._("print_copied_theme_folder", "Copied theme folder: {} to {}").format(source_path, theme_dir))

                    theme_txt = app.find_theme_txt(theme_dir)
                    if not theme_txt:
                        app.show_message_safe("warning", "warning_theme_txt_not_found_title", "warning_theme_txt_not_found_message",
                                              title_key=app._("warning_theme_txt_not_found_title", "Warning"),
                                              message_key=app._("warning_theme_txt_not_found_message", "theme.txt not found in processed theme '{}'. This theme might not work correctly.").format(theme_name))
                        if os.path.exists(theme_dir):
                            rel_theme_dir = os.path.relpath(theme_dir, drive).replace("\\", "/")
                            all_paths.add(f"/{rel_theme_dir}")
                    else:
                        rel_path = os.path.relpath(theme_txt, drive).replace("\\", "/")
                        all_paths.add(f"/{rel_path}")

                    all_fonts.update(app.find_pf2_fonts(theme_dir))
                    app.update_status_safe(0, app._("status_processed", "Processed {}").format(theme_name), 100 * processed_count / total)

                except Exception as e:
                    error_message = app._("error_processing_theme_message", "Error processing theme '{}': {}").format(theme_name, e)
                    print(error_message)
                    app.show_message_safe("error", "error_processing_theme_title", "", title_key=app._("error_processing_theme_title", "Processing Error"), message_key="", args=[error_message])
                    app.update_status_safe(0, app._("status_error_processing_theme", "Error processing {}").format(theme_name), 100 * processed_count / total)
                    continue
            else:
                app.update_status_safe(0, app._("status_skipped_existing_theme", "Skipped existing theme: {}").format(theme_name), 100 * processed_count / total)
                continue

        json_path = os.path.join(drive, support.VENTOY_JSON_PATH)
        try:
            config = ventoy_cfg.load_json_config(json_path)
            print(app._("print_loaded_existing_json", "Loaded existing ventoy.json"))
        except Exception as e:
            app.show_message_safe("error", "error_json_read_title", "error_json_read_message_existing",
                                  title_key=app._("error_json_read_title", "JSON Read Error"),
                                  message_key=app._("error_json_read_message_existing", "Failed to read existing ventoy.json: {}. Creating a new one.").format(e),
                                  args=[])
            config = {}

        ventoy_cfg.merge_theme_entries(config, all_paths, all_fonts)
        app.update_status_safe(0, app._("status_updating_json", "Updating ventoy.json..."), 100)
        try:
            ventoy_cfg.save_json_config(json_path, config)
            print(app._("print_saved_json_successfully", "Saved ventoy.json successfully."))
            app.update_status_safe(0, app._("status_themes_applied_success", "Themes applied and config updated successfully!"), 100)
            app.root.after(0, app.load_existing_themes)
        except Exception as e:
            app.show_message_safe("error", "error_json_write_title", "error_json_write_message",
                                  title_key=app._("error_json_write_title", "JSON Write Error"),
                                  message_key=app._("error_json_write_message", "Failed to save ventoy.json: {}.").format(e),
                                  args=[])
            app.update_status_safe(0, app._("status_task_failed", "Task failed."), 100)

    except Exception as e:
        error_message = app._("error_task_message", "An unexpected error occurred during task: {}\\n{}").format(str(e), traceback.format_exc())
        print(error_message)
        app.show_message_safe("error", "error_task_title", "", title_key=app._("error_task_title", "Task Error"), message_key="", args=[error_message])
        app.update_status_safe(0, app._("status_apply_theme_task_failed", "Theme application task failed."), 100)
    finally:
        app.set_buttons_state(tk.NORMAL)
        app.root.after(500, lambda: app.update_status_safe(0, app._("status_ready", "Status - READY"), 0))


def start_apply_theme_thread(app):
    if app.worker_thread and app.worker_thread.is_alive():
        app.show_message_safe("warning", "warning_busy_title", "warning_busy_message",
                              title_key=app._("warning_busy_title", "Busy"),
                              message_key=app._("warning_busy_message", "Another operation is already in progress."))
        return

    drive_display = app.drive_var.get()
    if not drive_display:
        app.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message",
                              title_key=app._("warning_select_drive_title", "Warning"),
                              message_key=app._("warning_select_drive_message", "Please select a drive first."))
        return

    if not app.theme_sources_paths:
        app.show_message_safe("warning", "warning_select_drive_title", "warning_no_theme_archive_selected_message",
                              title_key=app._("warning_select_drive_title", "Warning"),
                              message_key=app._("warning_no_theme_archive_selected_message", "No theme archive selected"))
        return

    app.current_drive = app.extract_drive_letter(drive_display)
    if not app.current_drive:
        app.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message",
                              title_key=app._("error_drive_letter_title", "Error"),
                              message_key=app._("error_drive_letter_message", "Could not determine drive letter."))
        return

    app.reset_status()
    app.set_buttons_state(tk.DISABLED)
    app.worker_thread = threading.Thread(target=apply_theme_task, args=(app, app.current_drive, app.theme_sources_paths.copy()))
    app.worker_thread.start()


def apply_settings_task(app, drive):
    try:
        json_path = os.path.join(drive, support.VENTOY_JSON_PATH)
        if not os.path.exists(json_path):
            app.show_message_safe("warning", "warning_ventoy_json_not_found_settings_title", "warning_ventoy_json_not_found_settings_message")
            return
        try:
            config = ventoy_cfg.load_json_config(json_path)
        except json.JSONDecodeError:
            app.show_message_safe("error", "error_json_read_settings_title", "error_json_read_settings_message", drive=drive)
            return
        except PermissionError:
            app.show_message_safe("error", "permission_error_title", "error_permission_read_json_settings_message", drive=drive)
            return
        except Exception as e:
            app.show_message_safe("error", "generic_error_title", "error_unexpected_read_json_settings_message", str(e))
            return

        theme_config = ventoy_cfg.ensure_theme_section(config)
        sel = app.default_theme_var.get()
        theme_paths_in_json = theme_config.get("file", [])
        theme_names_in_json = ventoy_cfg.get_theme_names_from_files(theme_paths_in_json)
        if sel == app._("option_random_theme", "Random Theme"):
            theme_config["default_file"] = 0
        elif sel and sel in theme_names_in_json:
            ventoy_cfg.update_default_theme(config, sel, theme_paths_in_json, random_label=app._("option_random_theme", "Random Theme"))
            if theme_config.get("default_file", 0) == 0:
                print(app._("print_warning_selected_default_theme_not_found_load", "Selected default theme '{}' not found in ventoy.json. Resetting to Random Theme.").format(sel))
                app.root.after(0, app.default_theme_var.set, app._("option_random_theme", "Random Theme"))
        else:
            app.show_message_safe("warning", "warning_select_drive_title", "warning_selected_default_theme_not_found", sel)
            if app._("option_random_theme", "Random Theme") not in app.default_theme_combo["values"]:
                current_values = list(app.default_theme_combo["values"])
                current_values.insert(0, app._("option_random_theme", "Random Theme"))
                app.root.after(0, app.default_theme_combo.config, {"values": current_values})
            app.root.after(0, app.default_theme_var.set, app._("option_random_theme", "Random Theme"))
            theme_config["default_file"] = 0

        resolution = app.resolution_var.get()
        ventoy_cfg.update_gfxmode(config, resolution, app.resolution_combo["values"])
        try:
            ventoy_cfg.save_json_config(json_path, config)
            app.root.after(0, app.load_existing_themes)
        except PermissionError:
            app.show_message_safe("error", "permission_error_title", "error_permission_write_json_settings_message", drive=drive)
            return
        except Exception as e:
            app.show_message_safe("error", "error_unexpected_settings_title", "error_unexpected_write_json_settings_message", str(e))
            return
    except Exception as e:
        app.show_message_safe("error", "error_unexpected_settings_title", "error_unexpected_settings_message", str(e), traceback.format_exc())
    finally:
        app.set_buttons_state(tk.NORMAL)


def start_apply_settings_thread(app):
    if app.worker_thread and app.worker_thread.is_alive():
        app.show_message_safe("warning", "warning_busy_title", "warning_busy_message",
                              title_key=app._("warning_busy_title", "Busy"),
                              message_key=app._("warning_busy_message", "Another operation is already in progress."))
        return

    drive_display = app.drive_var.get()
    if not drive_display:
        app.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message",
                              title_key=app._("warning_select_drive_title", "Warning"),
                              message_key=app._("warning_select_drive_message", "Please select a drive first."))
        return

    app.current_drive = app.extract_drive_letter(drive_display)
    if not app.current_drive:
        app.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message",
                              title_key=app._("error_drive_letter_title", "Error"),
                              message_key=app._("error_drive_letter_message", "Could not determine drive letter."))
        return

    app.set_buttons_state(tk.DISABLED)
    app.worker_thread = threading.Thread(target=apply_settings_task, args=(app, app.current_drive))
    app.worker_thread.start()


def remove_theme_task(app, drive, selected_theme):
    try:
        json_path = os.path.join(drive, support.VENTOY_JSON_PATH)
        theme_dir = os.path.join(drive, support.THEMES_DIR_NAME, selected_theme)
        MAX_STATUS_LENGTH = 50
        prefix_del = app._("status_deleting_theme_prefix", "Deleting theme '")
        suffix_del = app._("status_deleting_theme_suffix", "'...")
        available_length_del = MAX_STATUS_LENGTH - len(prefix_del) - len(suffix_del)
        short_name_del = selected_theme if len(selected_theme) <= available_length_del else selected_theme[:available_length_del - 3] + "..."
        app.update_status_safe(2, f"{prefix_del}{short_name_del}{suffix_del}", 10)
        try:
            if os.path.exists(theme_dir):
                shutil.rmtree(theme_dir)
                print(app._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_dir))
            else:
                print(app._("print_warning_theme_folder_not_found_skip", "Warning: Theme folder not found, skipping deletion: {}").format(theme_dir))
        except FileNotFoundError:
            print(app._("print_warning_theme_folder_not_found_during_delete", "Warning: Theme folder not found during deletion (already removed?): {}").format(theme_dir))
        except PermissionError:
            app.show_message_safe("error", "permission_error_title", "error_permission_deleting_folder",
                                  title_key=app._("permission_error_title", "Permission Error"),
                                  message_key=app._("error_permission_deleting_folder", "Permission denied while deleting folder: {}\\n\\nMake sure the folder is not in use and you have necessary permissions.").format(selected_theme),
                                  args=[])
            app.update_status_safe(2, app._("status_failed_delete_theme_folder", "Failed to delete theme folder."), 40)
            app.show_message_safe("warning", "warning_partial_deletion_title", "warning_partial_deletion_message_permission",
                                  title_key=app._("warning_partial_deletion_title", "Partial Deletion"),
                                  message_key=app._("warning_partial_deletion_message_permission", "Could not delete theme folder '{}' due to permissions. Attempting to update ventoy.json.").format(selected_theme),
                                  args=[])
        except Exception as e:
            app.show_message_safe("error", "generic_error_title", "error_unexpected_deleting_theme_folder",
                                  title_key=app._("generic_error_title", "Error"),
                                  message_key=app._("error_unexpected_deleting_theme_folder", "An unexpected error occurred while deleting theme folder: {}").format(str(e)),
                                  args=[])
            app.update_status_safe(2, app._("status_failed_delete_theme_folder", "Failed to delete theme folder."), 40)
            app.show_message_safe("warning", "warning_partial_deletion_title", "warning_partial_deletion_message_unexpected",
                                  title_key=app._("warning_partial_deletion_title", "Partial Deletion"),
                                  message_key=app._("warning_partial_deletion_message_unexpected", "Could not delete theme folder '{}' due to an unexpected error. Attempting to update ventoy.json.").format(selected_theme),
                                  args=[])

        app.update_status_safe(2, app._("status_updating_config", "Updating config file..."), 60)
        if os.path.exists(json_path):
            try:
                config = ventoy_cfg.load_json_config(json_path)
            except json.JSONDecodeError:
                app.show_message_safe("error", "error_json_read_remove_title", "error_json_read_remove_message",
                                      title_key=app._("error_json_read_remove_title", "JSON Error"),
                                      message_key=app._("error_json_read_remove_message", "Failed to read ventoy.json on {drive}. File might be corrupted. Cannot update config.").format(drive=drive),
                                      args=[])
                app.update_status_safe(2, app._("status_failed_update_config", "Failed to update config."), 100)
                app.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_json_error",
                                      title_key=app._("dialog_deletion_status_title", "Deletion Status"),
                                      message_key=app._("dialog_deletion_status_json_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to a JSON error.").format(selected_theme),
                                      args=[])
                app.root.after(0, app.load_existing_themes)
                return
            except PermissionError:
                app.show_message_safe("error", "permission_error_title", "error_permission_read_json_remove_message",
                                      title_key=app._("permission_error_title", "Permission Error"),
                                      message_key=app._("error_permission_read_json_remove_message", "Permission denied while reading ventoy.json on {drive}. Cannot update config.").format(drive=drive),
                                      args=[])
                app.update_status_safe(2, app._("status_failed_update_config", "Failed to update config."), 100)
                app.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_permission_error",
                                      title_key=app._("dialog_deletion_status_title", "Deletion Status"),
                                      message_key=app._("dialog_deletion_status_permission_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to a permission error.").format(selected_theme),
                                      args=[])
                app.root.after(0, app.load_existing_themes)
                return
            except Exception as e:
                app.show_message_safe("error", "generic_error_title", "error_unexpected_read_json_remove_message",
                                      title_key=app._("generic_error_title", "Error"),
                                      message_key=app._("error_unexpected_read_json_remove_message", "An unexpected error occurred while reading ventoy.json: {}").format(str(e)),
                                      args=[])
                app.update_status_safe(2, app._("status_failed_update_config", "Failed to update config."), 100)
                app.show_message_safe("info", "dialog_deletion_status_title", "dialog_deletion_status_unexpected_error",
                                      title_key=app._("dialog_deletion_status_title", "Deletion Status"),
                                      message_key=app._("dialog_deletion_status_unexpected_error", "Theme folder '{}' deletion attempted, but ventoy.json could not be updated due to an unexpected error.").format(selected_theme),
                                      args=[])
                app.root.after(0, app.load_existing_themes)
                return

            if "theme" in config:
                normalized_theme_dir_on_drive = os.path.normpath(theme_dir)

                def is_path_inside_deleted_theme_dir(ventoy_json_path):
                    if not ventoy_json_path or not isinstance(ventoy_json_path, str):
                        return False
                    try:
                        full_path_on_drive = os.path.normpath(os.path.join(drive, ventoy_json_path.lstrip("/")))
                        return full_path_on_drive.startswith(normalized_theme_dir_on_drive + os.sep) or full_path_on_drive == normalized_theme_dir_on_drive
                    except Exception:
                        return False

                ventoy_cfg.remove_theme_paths_from_config(config, is_path_inside_deleted_theme_dir)
                if config["theme"].get("default_file", 0) == 0:
                    print(app._("print_resetting_default_theme_to_random", "Resetting default theme to Random."))
                try:
                    ventoy_cfg.save_json_config(json_path, config)
                    print(app._("print_updated_json_successfully", "Updated ventoy.json successfully."))
                except PermissionError:
                    app.show_message_safe("error", "permission_error_title", "error_permission_write_json_settings_message",
                                          title_key=app._("permission_error_title", "Permission Error"),
                                          message_key=app._("error_permission_write_json_settings_message", "Permission denied while writing to ventoy.json on {drive}. Make sure you have write access.").format(drive=drive),
                                          args=[])
                    app.update_status_safe(2, app._("status_failed_update_config", "Failed to update config."), 100)
                    return
                except Exception as e:
                    app.show_message_safe("error", "generic_error_title", "error_unexpected_write_json_settings_message",
                                          title_key=app._("generic_error_title", "Error"),
                                          message_key=app._("error_unexpected_write_json_settings_message", "An unexpected error occurred while writing to ventoy.json: {}").format(str(e)),
                                          args=[])
                    app.update_status_safe(2, app._("status_failed_update_config", "Failed to update config."), 100)
                    return
            else:
                app.show_message_safe("info", "dialog_deletion_status_title", "info_themes_deleted_json_not_found_message",
                                      title_key=app._("dialog_deletion_status_title", "Deletion Status"),
                                      message_key=app._("info_themes_deleted_json_not_found_message", "Themes deleted, but ventoy.json not found."))

        app.update_status_safe(2, app._("status_config_update_processed", "Config update processed."), 80)
        app.root.after(0, app.load_existing_themes)
        prefix_done = app._("status_theme_deletion_finished_prefix", "Theme '")
        suffix_done = app._("status_theme_deletion_finished_suffix", "' deletion process finished.")
        available_length_done = MAX_STATUS_LENGTH - len(prefix_done) - len(suffix_done)
        short_name_done = selected_theme if len(selected_theme) <= available_length_done else selected_theme[:available_length_done - 3] + "..."
        app.update_status_safe(2, f"{prefix_done}{short_name_done}{suffix_done}", 100)

    except Exception as e:
        app.show_message_safe("error", "generic_error_title", "error_during_theme_deletion_task",
                              title_key=app._("generic_error_title", "Error"),
                              message_key=app._("error_during_theme_deletion_task", "Error during theme deletion task: {}\\n{}").format(str(e), traceback.format_exc()),
                              args=[])
        app.update_status_safe(2, app._("status_unexpected_error_deletion", "An unexpected error occurred during deletion."), 100)
    finally:
        app.set_buttons_state(tk.NORMAL)
        app.root.after(500, lambda: app.update_status_safe(2, app._("status_ready", "Status - READY"), 0))


def remove_all_themes_task(app, drive):
    try:
        theme_dir = os.path.join(drive, "ventoy", "theme")
        json_file_path = os.path.join(drive, support.VENTOY_JSON_PATH)
        themes_to_delete = []
        if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
            try:
                themes_to_delete = [item for item in os.listdir(theme_dir) if os.path.isdir(os.path.join(theme_dir, item))]
            except PermissionError:
                app.show_message_safe("error", "permission_error_title", "error_permission_listing_theme_dir")
                app.update_status_safe(2, app._("status_failed_list_themes_for_deletion", "Failed to list themes for deletion."), 100)
            except Exception as e:
                app.show_message_safe("error", "generic_error_title", "error_listing_theme_directory", str(e))
                app.update_status_safe(2, app._("status_failed_list_themes_for_deletion", "Failed to list themes for deletion."), 100)

        total = len(themes_to_delete)
        if total == 0:
            app.update_status_safe(2, app._("status_no_themes_found_in_directory", "No themes found in directory to delete."), 100)
        else:
            for idx, theme in enumerate(themes_to_delete, start=1):
                theme_path = os.path.join(theme_dir, theme)
                MAX_STATUS_LENGTH = 50
                prefix = app._("status_deleting_short_prefix", "Deleting ")
                suffix = app._("status_deleting_short_suffix", "...")
                max_length = MAX_STATUS_LENGTH - len(prefix) - len(suffix)
                short_name = theme if len(theme) <= max_length else theme[:max_length - 3] + "..."
                app.update_status_safe(2, f"{prefix}{short_name}{suffix}", (idx / total) * 100)
                try:
                    shutil.rmtree(theme_path)
                    print(app._("print_theme_folder_deleted", "Theme folder deleted: {}").format(theme_path))
                except FileNotFoundError:
                    print(app._("print_warning_theme_folder_not_found_during_delete", "Warning: Theme folder not found during deletion (already removed?): {}").format(theme_path))
                except PermissionError:
                    app.show_message_safe("error", "permission_error_title", "error_permission_deleting_folder", theme)
                    continue
                except Exception as e:
                    app.show_message_safe("error", "generic_error_title", "error_deleting_theme_file", theme, str(e))
                    continue

        if os.path.exists(json_file_path):
            try:
                app.update_status_safe(2, app._("status_updating_config", "Updating config file..."), 80)
                config = ventoy_cfg.load_json_config(json_file_path)
                ventoy_cfg.clear_theme_entries(config)
                ventoy_cfg.save_json_config(json_file_path, config)
                print(app._("print_updated_json_successfully", "Updated ventoy.json successfully."))
                app.update_status_safe(2, app._("status_config_update_processed", "Config update processed."), 90)
            except json.JSONDecodeError:
                app.show_message_safe("error", "error_json_read_remove_title", "error_json_corrupted_message")
                app.update_status_safe(2, app._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
            except PermissionError:
                app.show_message_safe("error", "permission_error_title", "error_permission_writing_ventoy_json_remove")
                app.update_status_safe(2, app._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
            except Exception as e:
                app.show_message_safe("error", "generic_error_title", "error_failed_update_ventoy_json_remove", str(e))
                app.update_status_safe(2, app._("status_failed_update_ventoy_json_remove", "Failed to update ventoy.json."), 100)
        elif total > 0:
            app.show_message_safe("info", "generic_info_title", "info_themes_deleted_json_not_found_message")

        app.update_status_safe(2, app._("status_all_themes_removed_config_updated", "All themes removed and config updated."), 100)
        app.root.after(0, app.load_existing_themes)
    except Exception as e:
        app.show_message_safe("error", "generic_error_title", "error_during_remove_all_themes_task", str(e), traceback.format_exc())
        app.update_status_safe(2, app._("status_unexpected_error_remove_all", "Unexpected error occurred."), 100)
    finally:
        app.set_buttons_state(tk.NORMAL)
        app.root.after(500, lambda: app.update_status_safe(2, app._("status_ready", "Status - READY"), 0))


def start_remove_theme_thread(app):
    if app.worker_thread and app.worker_thread.is_alive():
        app.show_message_safe("warning", "warning_busy_title", "warning_busy_message")
        return

    drive_display = app.drive_var.get()
    if not drive_display:
        app.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message")
        return

    selected = app.remove_theme_combo.get()
    if not selected or selected == app._("option_select_theme_to_delete", "Select a theme to delete"):
        app.show_message_safe("warning", "warning_select_drive_title", "warning_no_theme_selected_to_delete_message")
        return

    drive = app.extract_drive_letter(drive_display)
    theme_dir = os.path.join(drive, support.THEMES_DIR_NAME, selected)
    if not os.path.exists(theme_dir):
        app.show_message_safe("error", "generic_error_title", "error_theme_folder_not_found_message", theme_dir)
        app.root.after(0, app.load_existing_themes)
        return

    confirm = messagebox.askyesno(app._("dialog_confirm_delete_theme_title", "Confirm"),
                                  app._("dialog_confirm_delete_theme_message", "ARE YOU SURE YOU WANT TO DELETE THIS THEME?\\n\\nTHIS PROCESS CANNOT BE UNDONE!"))
    if not confirm:
        return

    app.current_drive = drive
    if not app.current_drive:
        app.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message")
        return

    app.reset_status()
    app.set_buttons_state(tk.DISABLED)
    app.worker_thread = threading.Thread(target=remove_theme_task, args=(app, app.current_drive, selected))
    app.worker_thread.start()


def start_remove_all_themes_thread(app):
    if app.worker_thread and app.worker_thread.is_alive():
        app.show_message_safe("warning", "warning_busy_title", "warning_busy_message")
        return

    drive_display = app.drive_var.get()
    if not drive_display:
        app.show_message_safe("warning", "warning_select_drive_title", "warning_select_drive_message")
        return

    drive = app.extract_drive_letter(drive_display)
    theme_dir = os.path.join(drive, "ventoy", "theme")

    has_themes_on_disk = False
    if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
        try:
            if any(os.path.isdir(os.path.join(theme_dir, item)) for item in os.listdir(theme_dir)):
                has_themes_on_disk = True
        except PermissionError:
            print(f"Permission denied checking theme directory: {theme_dir}")
        except Exception as e:
            print(f"Error checking theme directory {theme_dir}: {e}")

    if not has_themes_on_disk:
        app.show_message_safe("info", "generic_info_title", "info_no_themes_to_delete_message")
        return

    confirm = messagebox.askyesno(app._("dialog_confirm_delete_all_themes_title", "Confirm"),
                                  app._("dialog_confirm_delete_all_themes_message", "ARE YOU SURE YOU WANT TO DELETE ALL THEMES?"))
    if not confirm:
        return

    app.current_drive = drive
    if not app.current_drive:
        app.show_message_safe("error", "error_drive_letter_title", "error_drive_letter_message")
        return

    app.reset_status()
    app.set_buttons_state(tk.DISABLED)
    app.worker_thread = threading.Thread(target=remove_all_themes_task, args=(app, app.current_drive))
    app.worker_thread.start()

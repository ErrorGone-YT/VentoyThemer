from __future__ import annotations

import os
import shutil
import tarfile
import zipfile


def _translate(translate, key, default=None):
    if translate is None:
        return default if default is not None else key
    return translate(key, default)


def extract_theme_archive(archive_path, dest_path, translate=None):
    archive_path_lower = archive_path.lower()

    if archive_path_lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".zip", os.path.basename(archive_path)))
        except zipfile.BadZipFile:
            raise Exception(_translate(translate, "error_zip_bad_file", "Failed to extract .zip archive '{}': Not a valid ZIP file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_zip_extraction_error", "Failed to extract .zip archive '{}': {}").format(os.path.basename(archive_path), e))

    elif archive_path_lower.endswith(".zipx"):
        try:
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".zipx", os.path.basename(archive_path)))
        except zipfile.BadZipFile as e:
            raise Exception(_translate(translate, "error_zipx_bad_file", "Failed to extract .zipx archive '{}': Unsupported compression method or not a valid ZipX file. Error: {}").format(os.path.basename(archive_path), e))
        except Exception as e:
            raise Exception(_translate(translate, "error_zipx_extraction_error", "Failed to extract .zipx archive '{}': {}").format(os.path.basename(archive_path), e))

    elif archive_path_lower.endswith((".tar", ".tar.gz", ".tgz")):
        try:
            mode = "r:gz" if archive_path_lower.endswith((".tar.gz", ".tgz")) else "r"
            with tarfile.open(archive_path, mode) as tar_ref:
                tar_ref.extractall(dest_path)
            archive_type = ".tar.gz/.tgz" if mode == "r:gz" else ".tar"
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(archive_type, os.path.basename(archive_path)))
        except tarfile.ReadError:
            raise Exception(_translate(translate, "error_tar_read_error", "Failed to extract .tar/.tar.gz/.tgz archive '{}': Not a valid TAR/GZipped TAR file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_tar_extraction_error", "Failed to extract .tar/.tar.gz/.tgz archive '{}': {}").format(os.path.basename(archive_path), e))

    elif archive_path_lower.endswith(".tar.bz2"):
        try:
            with tarfile.open(archive_path, "r:bz2") as tar_ref:
                tar_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".tar.bz2", os.path.basename(archive_path)))
        except tarfile.ReadError:
            raise Exception(_translate(translate, "error_tarbz2_read_error", "Failed to extract .tar.bz2 archive '{}': Not a valid BZ2ipped TAR file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_tarbz2_extraction_error", "Failed to extract .tar.bz2 archive '{}': {}").format(os.path.basename(archive_path), e))

    elif archive_path_lower.endswith((".xz", ".tar.xz")):
        try:
            import lzma
        except ImportError:
            raise Exception(_translate(translate, "error_lzma_module_missing", "LZMA module not found. Cannot extract .xz archives."))

        temp_tar_path = os.path.join(dest_path, "temp_lzma_decompressed.tar")
        try:
            with lzma.open(archive_path, "rb") as f_in:
                os.makedirs(dest_path, exist_ok=True)
                with open(temp_tar_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            print(_translate(translate, "print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".xz", os.path.basename(archive_path)))

            with tarfile.open(temp_tar_path, "r") as tar_ref:
                tar_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".xz", os.path.basename(archive_path)))
        except tarfile.ReadError:
            raise Exception(_translate(translate, "error_tarxz_invalid_tar", "Decompressed file from .xz archive '{}' is not a valid tar archive. Please ensure it is a .tar.xz file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_tarxz_extraction_error", "Failed to decompress or extract .xz archive '{}': {}").format(os.path.basename(archive_path), e))
        finally:
            if os.path.exists(temp_tar_path):
                try:
                    os.remove(temp_tar_path)
                except Exception as e:
                    print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")

    elif archive_path_lower.endswith((".lz4", ".tar.lz4")):
        try:
            import lz4.frame
        except ImportError:
            raise Exception(_translate(translate, "error_lz4_module_missing", "The 'lz4' library is not installed. Please install it using 'pip install lz4'."))

        temp_tar_path = os.path.join(dest_path, "temp_lz4_decompressed.tar")
        try:
            with lz4.frame.open(archive_path, "rb") as f_in:
                os.makedirs(dest_path, exist_ok=True)
                with open(temp_tar_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            print(_translate(translate, "print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".lz4", os.path.basename(archive_path)))

            with tarfile.open(temp_tar_path, "r") as tar_ref:
                tar_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".lz4", os.path.basename(archive_path)))
        except tarfile.ReadError:
            raise Exception(_translate(translate, "error_tarlz4_invalid_tar", "Decompressed file from .lz4 archive '{}' is not a valid tar archive. Please ensure it is a .tar.lz4 file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_tarlz4_extraction_error", "Failed to decompress or extract .lz4 archive '{}': {}").format(os.path.basename(archive_path), e))
        finally:
            if os.path.exists(temp_tar_path):
                try:
                    os.remove(temp_tar_path)
                except Exception as e:
                    print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")

    elif archive_path_lower.endswith((".zst", ".tar.zst")):
        try:
            import zstandard
        except ImportError:
            raise Exception(_translate(translate, "error_zstd_module_missing", "The 'zstandard' library is not installed. Please install it using 'pip install zstandard'."))

        temp_tar_path = os.path.join(dest_path, "temp_zstd_decompressed.tar")
        try:
            dctx = zstandard.ZstdDecompressor()
            with open(archive_path, "rb") as f_in, open(temp_tar_path, "wb") as f_out:
                os.makedirs(dest_path, exist_ok=True)
                dctx.copy_stream(f_in, f_out)

            print(_translate(translate, "print_decompressed_and_extracting", "Decompressed {}. Attempting to extract temporary tar: {}").format(".zst", os.path.basename(archive_path)))

            with tarfile.open(temp_tar_path, "r") as tar_ref:
                tar_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".zst", os.path.basename(archive_path)))
        except tarfile.ReadError:
            raise Exception(_translate(translate, "error_tarzst_invalid_tar", "Decompressed file from .zst archive '{}' is not a valid tar archive. Please ensure it is a .tar.zst file.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_tarzst_extraction_error", "Failed to decompress or extract .zst archive '{}': {}").format(os.path.basename(archive_path), e))
        finally:
            if os.path.exists(temp_tar_path):
                try:
                    os.remove(temp_tar_path)
                except Exception as e:
                    print(f"Warning: Failed to remove temporary file '{temp_tar_path}': {e}")

    elif archive_path_lower.endswith(".7z"):
        try:
            import py7zr
        except ImportError:
            raise Exception(_translate(translate, "error_py7zr_module_missing", "The 'py7zr' library is not installed. Please install it using 'pip install py7zr'."))

        try:
            with py7zr.SevenZipFile(archive_path, mode="r") as szr:
                szr.extractall(path=dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".7z", os.path.basename(archive_path)))
        except py7zr.Bad7zFile:
            raise Exception(_translate(translate, "error_7z_bad_file", "Failed to extract .7z archive '{}': File is corrupted or not a valid 7z archive.").format(os.path.basename(archive_path)))
        except Exception as e:
            raise Exception(_translate(translate, "error_7z_extraction_error", "Failed to extract .7z archive '{}': {}").format(os.path.basename(archive_path), e))

    elif archive_path_lower.endswith(".rar"):
        try:
            import rarfile
        except ImportError:
            raise Exception(_translate(translate, "error_rarfile_module_missing", "The 'rarfile' library is not installed. Please install it using 'pip install rarfile' and ensure the 'unrar' utility is installed and available in your system's PATH."))

        try:
            with rarfile.RarFile(archive_path, "r") as rar_ref:
                rar_ref.extractall(dest_path)
            print(_translate(translate, "print_extracted_archive", "Extracted {} archive: {}").format(".rar", os.path.basename(archive_path)))
        except rarfile.RarCannotExec as e:
            raise Exception(_translate(translate, "error_rar_unrar_not_found", "Failed to extract .rar archive '{}'. The 'unrar' command was not found or could not be executed. Please install 'unrar' and ensure it is available in PATH. Error: {}").format(os.path.basename(archive_path), e))
        except rarfile.RarExtError as e:
            raise Exception(_translate(translate, "error_rar_rarfile", "Failed to extract .rar archive '{}'. Rarfile error: {}").format(os.path.basename(archive_path), e))
        except Exception as e:
            raise Exception(_translate(translate, "error_rar_unexpected", "An unexpected error occurred while extracting .rar archive '{}': {}").format(os.path.basename(archive_path), e))

    else:
        raise Exception(_translate(translate, "error_unsupported_archive_format", "Unsupported archive format for extraction: {}").format(os.path.basename(archive_path)))

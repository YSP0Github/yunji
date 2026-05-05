def read_text_file_with_fallback(file_path, chardet_module=None):
    """Read a text file, preferring UTF-8 and falling back to detected encoding."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read(), "utf-8"
    except UnicodeDecodeError:
        with open(file_path, "rb") as file:
            raw_data = file.read()

        if chardet_module is not None:
            result = chardet_module.detect(raw_data) or {}
            encoding = result.get("encoding") or "utf-8"
        else:
            encoding = "utf-8"

        with open(file_path, "r", encoding=encoding, errors="ignore") as file:
            return file.read(), encoding


def convert_size(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

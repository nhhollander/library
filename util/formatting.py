from datetime import datetime


def file_size(size: float):
    """
    Converts a number of bytes into a human-readable representation.
    """
    if size < 0:
        return "Invalid Size"
    sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    index = 0
    while size > 1024:
        size /= 1024
        index += 1
    return f"{size:0.3f}{sizes[index]}"


def timestamp_friendly(dt: datetime):
    """
    Converts a datetime (with timezone information) into a friendly timestamp.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")

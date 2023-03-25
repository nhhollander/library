from xdg import IconTheme  # type: ignore
import re
import config
from typing import cast
from threading import Lock


def __read_icon_file(path: str) -> dict[str, str]:
    """
    Loads the mime type to icon name mappings
    """
    with open(path, "r") as file:
        return {entry[0]: entry[1].strip() for entry in [line.split(":", 1) for line in file]}


__icons = __read_icon_file('/usr/share/mime/icons')
__icons_generic = __read_icon_file('/usr/share/mime/generic-icons')


def find_icon_name(mime_type: str) -> str:
    """
    Attempt to find the icon name in the icon mapping file.
    """
    icon_name = __icons.get(mime_type) or __icons_generic.get(mime_type)
    if not icon_name:
        # Attempt to use a generic identifier
        icon_name = mime_type.split("/")[0] + "-x-generic"
    return icon_name


# pyxdg is not thread safe, simultaneous access from multiple threads can result in `None` being
# improperly returned from the icon path lookup function.
__icon_lookup_lock = Lock()


def find_icon_path(icon_name: str):
    """
    Attempt to find the path to requested icon. A lock is required because the cache implementation
    in `IconTheme.getIconPath` contains multiple race conditions which caused it to return `None`
    incorrectly sporadically.
    """
    try:
        __icon_lookup_lock.acquire()
        return cast(str | None, IconTheme.getIconPath(icon_name, 256, theme='default'))
    finally:
        __icon_lookup_lock.release()


__browser_patterns: list[re.Pattern[str]] = \
    [re.compile(x) for x in config.configuration["site"]["nativeMimeTypes"]]


def is_browser_compatible(mime_type: str) -> bool:
    """
    Determine if the given mime type is able to be displayed directly in the browser.
    """
    for pattern in __browser_patterns:
        if pattern.match(mime_type):
            return True
    return False

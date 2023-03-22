from sqlite3 import Connection
from typing import Any
import numpy as np


def register(dbapi: Connection, _: Any):
    """
    Register custom functions with the internal sqlite3 connection object. This is required every
    time the connection is re-established.
    """
    dbapi.create_function('check_tags', 3, __check_tags)
    dbapi.create_function('has_tag', 2, __has_tag)


def __check_tags(_tags: bytes, _required: bytes, _forbidden: bytes):
    """
    Database function for checking if the requested set of tags matches all required tags and
    none of the forbidden tags.

    :param _tags: Tags assigned to the entry being tested
    :param _required: Array of tags which must be present in `_tags`
    :param _forbidden: Array of tags which must not be present in `_tags`
    :returns: True if all conditions are met
    """
    if _tags is None:
        _tags = b''
    tags = np.frombuffer(_tags, dtype=np.uint16)
    forbidden = np.frombuffer(_forbidden, dtype=np.uint16)
    # PERF: Is there a way to return False immediately on finding a tag?
    if len(_forbidden) > 0 and np.any(np.isin(tags, forbidden)):
        return False
    required = np.frombuffer(_required, dtype=np.uint16)
    return len(np.setdiff1d(required, tags)) == 0


def __has_tag(_tags: bytes, tag: int):
    """
    Database function for checking if the requested single tag is present in the given set of
    tags.

    :param _tags: Tags assigned to the entry being tested
    :param tag: Tag to check for
    :returns: True if the tag is present on the entry
    """
    tags = np.frombuffer(_tags, dtype=np.uint16)
    return tag in tags

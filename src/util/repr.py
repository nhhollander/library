from typing import Any


def repr_helper(object: Any, attrs: list[str]):
    """
    Helper method for generating a `repr` string from an object.

    Important Note: The value returned by this function should be passable to `eval()` such that
    an identical object is returned (see https://docs.python.org/3/library/functions.html#repr).
    """
    content = ', '.join(f"{a}={repr(getattr(object, a))}" for a in attrs)
    return f"{object.__class__.name}({content})"

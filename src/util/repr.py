from typing import Any


def repr_helper(object: Any, attrs: list[str]):
    """
    Helper method for generating a `repr` string from an object.

    Important Note: The value returned by this function should be passable to `eval()` such that
    an identical object is returned (see https://docs.python.org/3/library/functions.html#repr).
    """
    result = {}
    cname = type(object).__name__
    for key in attrs:
        if key.startswith("__"):
            mangled = f"_{cname}__{key[2:]}"
            result[key] = getattr(object, mangled)
        else:
            result[key] = getattr(object, key)
    content = ', '.join(f"{a}={result[a]}" for a in attrs)
    return f"{cname}({content})"

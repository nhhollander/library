from typing import Any

def plural(arg: Any):
    if isinstance(arg, int):
        return '' if arg == 1 else 's'
    else:
        return '' if len(arg) == 1 else 's'

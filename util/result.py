from typing import TypeVar, Generic, List, Any, Optional

T = TypeVar('T')

class Result(Generic[T]):

    value: Optional[T]
    warnings: List[Any]
    errors: List[Any]

    def __init__(self, value: Optional[T], warnings: Optional[List[Any]] = None, errors: Optional[List[Any]] = None, inherit: Optional['Result[T]'] = None):
        """
        Instantiate a new Result object.

        :param value: Value to return
        """
        self.value = value
        self.warnings = inherit.warnings if inherit else [] + warnings if warnings else []
        self.errors = inherit.errors if inherit else [] + errors if errors else []

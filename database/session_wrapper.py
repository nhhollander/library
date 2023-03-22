from typing import ParamSpec, TypeVar, Callable, Concatenate
from sqlalchemy.orm import Session

P = ParamSpec('P')
R = TypeVar('R')
Base = TypeVar('Base')
WithoutSession = Callable[Concatenate[Base, P], R]
WithSession = Callable[Concatenate[Base, Session, P], R]


def with_session(f: WithSession[Base, P, R]) -> WithoutSession[Base, P, R]:
    """
    Provide an automatically closing session object to the wrapped function. Decorating a function
    with this wrapper is functionally equivalent to wrapping the contents of the target function in
    a `with self.__scoped_session() as session:` block.
    :param f: Function to wrap. Must be a class member of `Database` that accepts a `Session` as the
              second parameter after `self`.
    """
    def wrapper(base: Base, *args: P.args, **kwargs: P.kwargs) -> R:
        session: Session = base.get_session()  # type: ignore
        result = f(base, session, *args, **kwargs)
        session.close()
        return result
    return wrapper

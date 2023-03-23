from typing import Type, Literal, Callable, TypeVar, cast, ParamSpec, Concatenate, Any
from functools import wraps
from flask import jsonify, request, Response, render_template
from util.timer import Timer
from util.validator import ValidationException, Validator
import dateutil.parser
import json
import traceback
from typing_extensions import TypedDict
from database import Database
import server

validator = Validator(raise_exception=True)


# ========== #
# Decorators #
# ========== #

P = ParamSpec('P')
R = TypeVar('R')
GenericDict = TypeVar('GenericDict', bound=TypedDict)


def args(argType: Type[GenericDict], method: Literal['GET', 'POST'] = 'GET'):
    """
    Decorator generator for retrieving and validating request arguments. When the `method` is set to
    `GET` arguments will be retrieved from `request.args`. When the `method` is set to `POST`
    arguments will be read from the request body and parsed as json. TODO: Support for native
    encoding types as well

    :param argType: TypedDict defining required and optional request values.
    :param method: Which arg source to retrieve from.
    :returns: A decorator which provides a valid argument object to the decorated function.
    """
    def decorator(function: Callable[Concatenate[GenericDict, P], R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            # Get data depending on source
            if method == 'GET':
                data = request.args
            elif method == 'POST':
                data = json.loads(request.get_data(as_text=True))
            try:
                validator.validate(data, argType)
                arguments = cast(argType, data)
            except ValidationException as e:
                raise RequestError({
                    "message": "Invalid Request",
                    "detail": e.message
                })
            return function(arguments, *args, **kwargs)
        return wrapper
    return decorator


def exceptionWrapper(function: Callable[P, R]) -> Callable[P, R | tuple[Response, int]]:
    """
    Wrapper that catches request errors and unhandled exceptions and converts them into an
    appropriate response object.

    This decorator converts `RequestError`s and uncaught `Exception`s into appropriate response
    objects.

    :param function: The function to wrap.
    :returns: A wrapper that handles exceptions.
    """
    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        try:
            return function(*args, **kwargs)
        except RequestError as e:
            return jsonify({
                "result": "error",
                "detail": e.detail,
            }), e.code
        except Exception as e:
            traceback.print_exception(e)
            return jsonify({
                "result": "error",
                "detail": f"Uncaught exception of type {type(e).__name__}"
            }), 500

    return wrapper


def withDatabase(function: Callable[Concatenate[Database, P], R]) -> Callable[P, R]:
    """
    Provides database access to a handler, ensuring that resources allocated to handle this
    transaction are released as soon as the handler completes.
    """
    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        db = server.get_db_internal()
        res = function(db, *args, **kwargs)
        db.release()
        return res
    return wrapper


FullTuple = tuple[str, dict[str, Any], int]
PartialTuple = tuple[str, dict[str, Any]]
TemplateFunc = Callable[P, PartialTuple | FullTuple]


def templateWrapper(function: TemplateFunc[P]) -> Callable[P, Response]:
    """
    Wrapper for `render_template` that includes some useful additional values shared between many
    pages.
    """
    def expand(input: PartialTuple | FullTuple) -> FullTuple:
        """
        Wrapper to add the optional status code parameter to the return tuple.
        """
        return input if len(input) == 3 else (input + (200,))

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        timer = Timer()
        template_name, params, status = expand(function(*args, **kwargs))
        params['query_time'] = timer.time_formatted()
        resp = Response(render_template(template_name, **params))
        resp.status_code = status
        return resp
    return wrapper


# ===== #
# Types #
# ===== #

class RequestError(Exception):
    """
    A RequestError represents a fatal error caused either by bad user input (4xx) or an internal
    server error (5xx). This exception is intended to be caught by the `@exceptionWrapper`
    decorator.
    """
    def __init__(self, detail: object, code: int = 400):
        self.detail = detail
        self.code = code
        self.args = (detail, code)


# ================ #
# Helper Functions #
# ================ #

def success(data: object) -> tuple[Response, int]:
    """
    Simple wrapper to generate a successful response from any object.

    :param data: Any JSON serializable object.
    :returns: A tuple containing a JSON response object and a 200 status code.
    """
    return jsonify({
        "result": "success",
        "detail": data
    }), 200


def parse_date(date: str | None, key: str):
    """
    Attempt to parse a date. If the given input is `None` or an empty screen, this function will
    return `None`.

    :param date: Date string to parse
    :param key: Key used for debug/error reporting
    :returns: The parsed date or None if no date was given
    """
    if date == "" or date is None:
        return None
    try:
        return dateutil.parser.parse(date)
    except dateutil.parser.ParserError as e:
        raise RequestError({
            "message": f"Invalid date for key '{key}': {str(e)}"
        })

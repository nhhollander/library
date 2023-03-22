from typing import Type, Literal, Callable, TypeVar, Any, cast
from functools import wraps
from flask import jsonify, request, Response
from util.validator import ValidationException, Validator
from util.plural import plural
import dateutil.parser
import json
import traceback
from typing_extensions import TypedDict
import server

GenericDict = TypeVar('GenericDict', bound=TypedDict)
validator = Validator(raise_exception=True)

def args(argType: Type[GenericDict], method: Literal['GET', 'POST'] = 'GET'):
    """
    Decorator generator for retrieving and validating request arguments. When the `method` is set to
    `GET` arguments will be retrieved from `request.args`. When the `method` is set to `POST`
    arguments will be read from 

    :param argType: TypedDict defining required and optional request values.
    :param method: Which arg source to retrieve from.
    :returns: A decorator which provides a valid argument object to the decorated function.
    """
    def decorator(function: Callable[[GenericDict], Any]):
        @wraps(function)
        def wrapper():
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
            return function(arguments)
        return wrapper
    return decorator

def exceptionWrapper(function: Callable[..., Any]):
    """
    Wrapper that catches request errors and unhandled exceptions and converts them into an
    appropriate response object.

    This decorator converts `RequestError`s and uncaught `Exception`s into appropriate response
    objects.

    :param function: The function to wrap.
    :returns: A wrapper that handles exceptions.
    """
    @wraps(function)
    def wrapper():
        try:
            return function()
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

def parse_date(date: str|None, key: str):
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

def validate_tags(tags: list[str]):
    """
    Attempt to validate the given tags. Raises a `RequestError` if the validation fails.

    :param db: Database instance to query for tag validity
    :param tags: List of tags to validate
    """
    invalid = server.db.check_tags(tags)
    if len(invalid) > 0:
        raise RequestError({
            "message": f"Invalid tag{plural(invalid)}",
            "invalid_tags": invalid
        })

from database import Database
from flask import jsonify, request, Response, render_template
from functools import wraps
from markdown2 import Markdown  # type: ignore
from typing import Type, Literal, Callable, TypeVar, cast, ParamSpec, Concatenate, Any
from typing_extensions import TypedDict, NotRequired
from util import formatting
from util.timer import Timer
from util.validator import ValidationException, Validator
from werkzeug.wrappers import Response as WerkzeugResponse
import dateutil.parser
import json
import server
import traceback

validator = Validator(raise_exception=True)
markdowner = Markdown()


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


FullTuple = tuple[str, dict[str, Any] | TypedDict, int]
PartialTuple = tuple[str, dict[str, Any] | TypedDict]
# Required because flask's response object isn't 100% compatible with the internal Werkzeug response
GeneralResponse = Response | WerkzeugResponse
TemplateFuncReturnType = PartialTuple | FullTuple | GeneralResponse
TemplateFunc = Callable[P, TemplateFuncReturnType]


class AdditionalTemplateFields(TypedDict):
    query_time: str
    total_data: str
    entry_count: str
    db_size: str
    formatting: Any  # Module type?
    markdown: Callable[[Any], Any]


def templateWrapper(function: TemplateFunc[P]) -> Callable[P, GeneralResponse]:
    """
    Wrapper for `render_template` that includes some useful additional values shared between many
    pages. If the wrapped function returns a response object, it will be passed through unmodified.
    """
    def expand(input: PartialTuple | FullTuple) -> FullTuple:
        """
        Wrapper to add the optional status code parameter to the return tuple.
        """
        return input if len(input) == 3 else (input + (200,))  # type: ignore

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        timer = Timer()
        raw_response = function(*args, **kwargs)
        if isinstance(raw_response, Response) or isinstance(raw_response, WerkzeugResponse):
            return raw_response

        template_name, params, status = expand(raw_response)
        db = server.get_db_internal()
        params = cast(AdditionalTemplateFields, params)  # Strip away any special typing information
        params['query_time'] = timer.time_formatted()
        params['total_data'] = formatting.file_size(db.total_size())
        params['entry_count'] = f"{db.entry_count():,}"
        params['db_size'] = formatting.file_size(db.database_size())
        params['formatting'] = formatting
        params['markdown'] = markdowner.convert
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


class Message:
    class_: str
    message: str

    def __init__(self, class_: str, message: str):
        self.class_ = class_
        self.message = message


Err: Callable[[str], Message] = lambda message: Message('error', message)
Warning: Callable[[str], Message] = lambda message: Message('warning', message)
Success: Callable[[str], Message] = lambda message: Message('success', message)


class StandardRenderParams(TypedDict):
    """
    A set of parameters found on most pages.
    """
    query: NotRequired[str]
    messages: NotRequired[list[Message]]


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

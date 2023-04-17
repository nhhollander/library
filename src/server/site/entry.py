from database.types import EntryUpdateParams
from server.helpers import exceptionWrapper, templateWrapper, args, withDatabase
from server.helpers import StandardRenderParams, Err, Message, TemplateFuncReturnType
from database import Database
from database.entry import Entry
from database.exceptions import InvalidTagException
from typing_extensions import TypedDict, NotRequired
from util import mime
from flask import request, redirect
from util.validator import ValidationException, Validator
from dateutil.parser import parser
from typing import Callable, Any
import re


class EntryArgs(TypedDict):
    id: str
    q: NotRequired[str]


@exceptionWrapper
@args(EntryArgs)
@withDatabase
@templateWrapper
def entry(db: Database, args: EntryArgs):
    class Params(StandardRenderParams):
        entry: Entry | None
        native: bool
    render_params: Params = {
        'query': args.get('q') or '',
        'messages': [],
        'entry': None,
        'native': False
    }

    try:
        id = int(args['id'])
    except Exception as e:
        render_params['messages'].append(Err(f"Invalid Entry ID: {e.args[0]}"))
        return 'entry.html', render_params, 400

    render_params['entry'] = db.get_entry_by_id(id)
    if not render_params['entry']:
        render_params['messages'].append(Err(f"Entry {id} not found"))
        return 'entry.html', render_params, 404
    if not render_params['entry'].storage_id:
        render_params['messages'].append(Err(f"Entry {id} has no associated media"))
        return 'entry.html', render_params
    render_params['native'] = mime.is_browser_compatible(render_params['entry'].mime_type or '')
    if not render_params['native']:
        render_params['messages'].append(
            Err(f"Entry {id} (type {render_params['entry'].mime_type}) can not be displayed "
                "in-browser"))

    return 'entry.html', render_params


@exceptionWrapper
@args(EntryArgs)
@withDatabase
@templateWrapper
def edit_entry(db: Database, args: EntryArgs) -> TemplateFuncReturnType:
    class Params(StandardRenderParams):
        entry: Entry | None
        stale_error: dict[str, str]
    render_params: Params = {
        'query': args.get('q') or '',
        'messages': [],
        'entry': None,
        'stale_error': {}
    }

    # Validate request
    try:
        id = int(args['id'])
    except ValueError as e:
        render_params['messages'].append(Err(f"Invalid Entry  Id: {e.args[0]}"))
        return 'entry_edit.html', render_params, 400

    render_params['entry'] = db.get_entry_by_id(id)
    if not render_params['entry']:
        render_params['messages'].append(Err(f"Entry {id} not found"))
        return 'entry_edit.html', render_params, 404

    # If request was done via POST, parse and validate the arguments.
    if request.method == "POST":
        message = handle_entry_update(db, render_params['entry'])
        if message:
            render_params['messages'].append(message)
            # Populate input values back to the page so the user doesn't lose their data
            render_params['stale_error'] = request.form
        else:
            # Success! Redirect the user back to the post page
            return redirect(f"/entry?id={render_params['entry'].id}", code=303)

    return 'entry_edit.html', render_params


def handle_entry_update(db: Database, entry: Entry) -> Message | None:
    new_data: EntryUpdateParams = {}
    validator = Validator(True)

    # Preprocess and validate
    try:
        form = request.form
        no_op: Callable[[str], str] = lambda x: x

        def load(key: str, none_on_blank: bool, transform: Callable[[str], Any] = no_op):
            """
            Interpret a request value.
            :param key: The key to interpret. Should match the request and entry objects.
            :param none_on_blank: Treat an empty sting as `None`.
            :transform: Transformation function.
            """
            if key not in form:
                return
            if form[key] == '' and none_on_blank:
                new_data[key] = None
            else:
                new_data[key] = transform(form[key])

        load('item_name', True)
        load('storage_id', True)
        load('tags', False, parse_tag_str)
        load('description', True)
        load('transcription', True)
        load('date_created', False, parse_date_str)
        load('date_digitized', False, parse_date_str)
        load('location', True)

        validator.validate(new_data, EntryUpdateParams)
    except DateParseException as e:
        return Err(e.message)
    except ValidationException as e:
        return Err(e.message)
    except Exception as e:
        return Err(f"Uncaught exception of type {type(e).__name__}: {e}")

    try:
        entry.update_safe(new_data)
    except InvalidTagException as e:
        print(e)
        return Err(e.message)


class DateParseException(Exception):
    """
    Special wrapper exceptions that contains all possible exceptions raised by the date string
    parser.
    """
    base_exception: Exception
    message: str

    def __init__(self, base: Exception):
        self.base_exception = base
        self.message = f"Failed to parse date, got {type(base).__name__}: {base}"


def parse_date_str(raw: str):
    """
    Attempt to parse a complete date/time string into a unix timestamp
    """
    try:
        p = parser()
        return p.parse(raw)
    except Exception as e:
        raise DateParseException(e)


def parse_tag_str(raw: str) -> list[str]:
    """
    Process the value of a tag field.
    """
    x = re.sub(r"\s+", " ", raw)
    if x == "":
        return []
    return x.split(' ')

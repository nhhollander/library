from flask import Blueprint
from database.exceptions import InvalidTagException, DatabaseException
from server.helpers import RequestError, exceptionWrapper, args, templateWrapper, withDatabase
from typing_extensions import TypedDict, NotRequired
from typing import Any
from database import searchStringParser, Database

site = Blueprint('site', __name__)


@site.route("/")
@templateWrapper
def index():
    x: dict[str, str] = {}
    return 'index.html', x


class SearchArgs(TypedDict):
    q: str
    page: NotRequired[str]


@site.route("/search")
@exceptionWrapper
@args(SearchArgs)
@withDatabase
@templateWrapper
def search(db: Database, args: SearchArgs):
    render_params: dict[str, Any] = {
        "query": args['q'],
        "entries": [],
        "warnings": [],
        "search_time": 0
    }

    try:
        query = args['q']
        if 'page' in args:
            query += f" page:{args['page']}"
        params, warnings = searchStringParser.parse_search(query)
        render_params['warnings'].extend(warnings)
        render_params['entries'] = db.search(params)
    except InvalidTagException as e:
        if len(e.tags) > 1:
            warn = f"Query contains invalid tags: {', '.join(e.tags)}"
        else:
            warn = f"Query contains an invalid tag: {e.tags[0]}"
        render_params['warnings'].append(warn)
    except DatabaseException as e:
        render_params['warnings'].append(f"Uncaught database exception {type(e).__name__}")

    return 'search.html', render_params


class EntryArgs(TypedDict):
    id: str
    q: NotRequired[str]


@site.route("/entry")
@exceptionWrapper
@args(EntryArgs)
@withDatabase
@templateWrapper
def entry(db: Database, args: EntryArgs):
    render_params: dict[str, Any] = {
        "query": args.get('q'),
        "entry": None
    }

    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")

    render_params['entry'] = db.get_entry_by_id(id)
    if not render_params['entry']:
        raise RequestError(f"No such entry {id}", 404)
    if not render_params['entry'].storage_id:
        raise RequestError("Entry has no associated media", 404)

    return 'entry.html', render_params

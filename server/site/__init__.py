from flask import Blueprint, render_template
from database.exceptions import InvalidTagException
from server.helpers import RequestError, exceptionWrapper, args, withDatabase
from typing_extensions import TypedDict, NotRequired
from typing import Any
from database import searchStringParser, Database
import time

site = Blueprint('site', __name__)


@site.route("/")
def index():
    return render_template('index.html', message='hello')


class SearchArgs(TypedDict):
    q: str
    page: NotRequired[str]


@site.route("/search")
@exceptionWrapper
@args(SearchArgs)
@withDatabase
def search(db: Database, args: SearchArgs):
    render_params: dict[str, Any] = {
        "query": args['q'],
        "entries": [],
        "warnings": [],
        "search_time": 0
    }

    search_start_time = time.time()
    try:
        query = args['q']
        if 'page' in args:
            query += f" page:{args['page']}"
        render_params['entries'] = db.search(searchStringParser.parse_search(query))
    except InvalidTagException as e:
        if len(e.tags) > 1:
            warn = f"Your query contains invalid tags: [{', '.join(e.tags)}]"
        else:
            warn = f"Your query contains an invalid tag: {e.tags[0]}!"
        render_params['warnings'].append(warn)
    render_params["search_time"] = f"{(time.time() - search_start_time) * 1000:.3f}ms"

    return render_template('search.html', **render_params)


class EntryArgs(TypedDict):
    id: str
    q: NotRequired[str]


@site.route("/entry")
@exceptionWrapper
@args(EntryArgs)
@withDatabase
def entry(db: Database, args: EntryArgs):
    render_params: dict[str, Any] = {
        "query": args.get('q'),
        "entry": None
    }
    # Validate input and entry
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")
    render_params['entry'] = db.get_entry_by_id(id)
    if not render_params['entry']:
        raise RequestError(f"No such entry {id}", 404)
    if not render_params['entry'].storage_id:
        raise RequestError("Entry has no associated media", 404)

    print(render_params)

    return render_template('entry.html', **render_params)

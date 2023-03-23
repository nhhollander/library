from flask import Blueprint
from database.entry import Entry
from database.exceptions import InvalidTagException, DatabaseException
from server.helpers import exceptionWrapper, args, templateWrapper, withDatabase
from server.helpers import StandardRenderParams, Warning, Err
from typing_extensions import TypedDict, NotRequired
from database import searchStringParser, Database
from util import mime

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
    class Params(StandardRenderParams):
        entries: list[Entry]
    render_params: Params = {
        'query': args['q'],
        'messages': [],
        'entries': []
    }

    try:
        query = args['q']
        if 'page' in args:
            query += f" page:{args['page']}"
        params, warnings = searchStringParser.parse_search(query)
        render_params['messages'].extend(Warning(w) for w in warnings)
        render_params['entries'] = db.search(params)
    except InvalidTagException as e:
        if len(e.tags) > 1:
            message = f"Query contains invalid tags: {', '.join(e.tags)}"
        else:
            message = f"Query contains an invalid tag: {e.tags[0]}"
        render_params['messages'].append(Err(message))
    except DatabaseException as e:
        message = f"Uncaught database exception {type(e).__name__}"
        render_params['messages'].append(Err(message))

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

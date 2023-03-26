from flask import Blueprint
from database.entry import Entry
from database.exceptions import InvalidTagException, DatabaseException
from server.helpers import exceptionWrapper, args, templateWrapper, withDatabase
from server.helpers import StandardRenderParams, Warning, Err
from typing_extensions import TypedDict, NotRequired
from database import searchStringParser, Database

from .credits import credits
from .tags import tags
from .entry import entry, edit_entry

site = Blueprint('site', __name__)

site.add_url_rule('/credits', '/credits', credits)
site.add_url_rule('/tags', '/tags', tags)
site.add_url_rule('/entry', '/entry', entry)
site.add_url_rule('/editEntry', '/editEntry', edit_entry, methods=['GET', 'POST'])


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

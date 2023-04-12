from server.helpers import exceptionWrapper, templateWrapper, args, withDatabase
from server.helpers import StandardRenderParams, Err, Warning
from database import searchStringParser, Database
from database.entry import Entry
from database.exceptions import DatabaseException, InvalidTagException
from typing_extensions import TypedDict, NotRequired


class SearchArgs(TypedDict):
    q: str
    page: NotRequired[str]


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
        render_params['messages'].append(Err(e.message))
    except DatabaseException as e:
        message = f"Uncaught database exception {type(e).__name__}"
        render_params['messages'].append(Err(message))

    if len(render_params['entries']) == 0:
        render_params['messages'].append(Err("No results"))

    return 'search.html', render_params

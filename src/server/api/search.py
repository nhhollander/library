from flask import Blueprint
from server.helpers import exceptionWrapper, args
from typing_extensions import TypedDict

search_api = Blueprint('search_api', __name__, url_prefix='/search')


class SearchArgs(TypedDict):
    query: str


@search_api.route("")
@exceptionWrapper
@args(SearchArgs)
def search(args: SearchArgs):
    # Parse the query string
    pass

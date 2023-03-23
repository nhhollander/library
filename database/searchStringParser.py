import time

from .types import SearchParameters
from dateutil import parser


def parse_search(query: str) -> tuple[SearchParameters, list[str]]:
    """
    Parse a search query string into a SearchParameters object. A list of issues with the query is
    included in the second result parameter.
    """
    params: SearchParameters = {}
    issues: list[str] = []

    for token in [x for x in query.split(" ") if len(x) > 0]:
        print(token)
        if ':' in token:
            __parse_special(token, params, issues)
        else:
            __parse_standard(token, params, issues)

    return params, issues


def __parse_special(token: str, params: SearchParameters, issues: list[str]):
    """
    Special queries consist of a command and a value separated by a colon.
    """
    command, value = token.split(":", 1)

    # Parse date entries
    def special_datetime(key: str):
        if command == key:
            params[key] = __parse_datetime(value, issues)
    special_datetime('since')
    special_datetime('until')
    special_datetime('since_modified')
    special_datetime('until_modified')
    special_datetime('since_digitized')
    special_datetime('until_digitized')
    special_datetime('since_indexed')
    special_datetime('until_indexed')

    if command == "page":
        try:
            params['page'] = int(value)
        except ValueError:
            params['page'] = -1


def __parse_standard(token: str, params: SearchParameters, issues: list[str]):
    """
    Standard queries are interpreted as required or forbidden tags.
    """
    if token[0] == "-":
        tag = token[1:]
        if len(tag) == 0:
            issues.append("Query contains a stray hyphen")
            return
        if 'f_tags' not in params:
            params['f_tags'] = []
        params['f_tags'].append(tag)
    else:
        if 'tags' not in params:
            params['tags'] = []
        params['tags'].append(token)


SECONDS_IN_YEAR = 31557600
SECONDS_IN_MONTH = 2592000
SECONDS_IN_WEEK = 604800
SECONDS_IN_DAY = 86400


def __parse_datetime(token: str, issues: list[str]) -> int:
    # Parse "yester-times"
    if token == "yesteryear":
        return int(time.time() - SECONDS_IN_YEAR)
    elif token == "yestermonth":
        return int(time.time() - SECONDS_IN_MONTH)
    elif token == "yesterweek":
        return int(time.time() - SECONDS_IN_WEEK)
    elif token == "yesterday":
        return int(time.time() - SECONDS_IN_DAY)

    # Parse ISO dates
    try:
        return int(time.mktime(parser.parse(token).utctimetuple()))
    except parser.ParserError:
        issues.append(f"{token} is not a valid timestamp")
        return 0

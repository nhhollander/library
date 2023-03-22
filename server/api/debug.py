from flask import Blueprint
from database.types import EntryUpdateParams
import server
from server.helpers import exceptionWrapper

debug_api = Blueprint("debug_api", __name__, url_prefix="/debug")


@debug_api.route("/createEntries")
@exceptionWrapper
def createEntries():
    tags: list[str] = [
        'Tag1', 'Tag2', 'Tag3', 'Tag4'
    ]
    test_definitions: list[EntryUpdateParams] = [
        {
            'item_name': 'Test Entry 1',
            'tags': ['Tag1', 'Tag2', 'Tag3', 'Tag4']
        },
        {
            'item_name': 'Test Entry 2',
            'tags': ['Tag1', 'Tag2', 'Tag3', 'Tag4']
        },
        {
            'item_name': 'Test Entry 2',
            'tags': ['Tag1', 'Tag3']
        },
        {
            'item_name': 'Test Entry 3',
            'tags': ['Tag2', 'Tag4']
        },
        {
            'item_name': 'Test Entry 4',
            'tags': ['Tag1']
        },
        {
            'item_name': 'Test Entry 5',
            'tags': ['Tag2']
        },
        {
            'item_name': 'Test Entry 6',
            'tags': ['Tag3']
        },
        {
            'item_name': 'Test Entry 7',
            'tags': ['Tag4']
        }
    ]

    for tag in tags:
        server.db.create_tag(tag)
    for definition in test_definitions:
        e = server.db.create_entry()
        e.update_safe(definition)
    return "Success"

from flask import Blueprint
from database.types import EntryUpdateParams
from database.entry import Entry
from server.helpers import exceptionWrapper, withDatabase
from database import Database

debug_api = Blueprint("debug_api", __name__, url_prefix="/debug")


@debug_api.route("/createEntries")
@exceptionWrapper
@withDatabase
def createEntries(db: Database):
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
        db.create_tag(tag)
    for definition in test_definitions:
        e = db.create_entry()
        e.update_safe(definition)
    return "Success"


@debug_api.route("/foo")
@exceptionWrapper
@withDatabase
def foo(db: Database): 
    db.foo_foo_foo().query(Entry.tags_raw).where(Entry.id == 7).one()

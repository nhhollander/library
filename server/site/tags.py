from database import Database
from database.exceptions import TagDoesNotExistException, TagExistsException
from database.tag import Tag
from typing_extensions import TypedDict, NotRequired
from server.helpers import StandardRenderParams, args, exceptionWrapper, templateWrapper, Err
from server.helpers import withDatabase, Message, Success


class TagActions(TypedDict):
    action: NotRequired[str]
    tag: NotRequired[str]
    new_tag: NotRequired[str]


@exceptionWrapper
@args(TagActions)
@withDatabase
@templateWrapper
def tags(db: Database, args: TagActions):
    class Params(StandardRenderParams):
        tags: list[Tag]
    render_params: Params = {
        'messages': [],
        'tags': []
    }

    # Check for action
    if 'action' in args:
        render_params['messages'].append(__process_actions(db, args))

    render_params['tags'] = db.get_all_tags()

    return 'tags.html', render_params


def __process_actions(db: Database, args: TagActions) -> Message:
    if 'action' not in args:
        # This should never happen
        raise RuntimeError("Missing action")

    if 'tag' not in args or args['tag'] == '':
        return Err("Missing required parameter 'tag'")

    if args['action'] == 'create':
        return __create(db, args['tag'])
    if args['action'] == 'delete':
        return __delete(db, args['tag'], args.get('new_tag'))
    if args['action'] == 'rename':
        return __rename(db, args['tag'], args.get('new_tag'))

    return Err(f"Invalid action '{args['action']}")


def __create(db: Database, tag: str) -> Message:
    try:
        db.create_tag(tag)
        return Success(f"Created tag {tag}")
    except TagExistsException:
        return Err(f"Tag {tag} already exists!")


def __delete(db: Database, tag: str, new_tag: str | None) -> Message:
    if new_tag == '':
        new_tag = None

    try:
        db.delete_tag(tag, new_tag)
        if new_tag:
            return Success(f"Deleted tag {tag} and replaced with {new_tag}")
        else:
            return Success(f"Deleted tag {tag}")
    except TagDoesNotExistException as e:
        replace = f" and replace with {new_tag}" if new_tag else ''
        return Err(f"Failed to delete '{tag}'{replace}: Tag '{e.tag}' does not exist")


def __rename(db: Database, tag: str, new_tag: str | None) -> Message:
    if new_tag == '' or new_tag is None:
        return Err("Missing required parameter 'new_tag'")

    try:
        db.rename_tag(tag, new_tag)
        return Success(f"Renamed tag {tag} to {new_tag}")
    except TagDoesNotExistException:
        return Err(f"Rename Failed: Tag '{tag}' does not exist")
    except TagExistsException:
        return Err(f"Rename Failed: Tag '{new_tag}' already exists")

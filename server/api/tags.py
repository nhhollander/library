from flask import Blueprint
from typing_extensions import TypedDict, NotRequired

from server.helpers import exceptionWrapper, success, args, RequestError
import server

from database.exceptions import TagExistsException, TagDoesNotExistException

tag_api = Blueprint('tag_api', __name__, url_prefix='/tags')

@tag_api.route("/list")
@exceptionWrapper
def listTags():
    return success(server.db.get_all_tags())

from typing import TypeVar

GenericDict = TypeVar('GenericDict', bound=TypedDict)

class CreateTagArgs(TypedDict):
    tag: str
@tag_api.route("/create")
@exceptionWrapper
@args(CreateTagArgs)
def createTag(args: CreateTagArgs):
    # Attempt to create
    try:
        server.db.create_tag(args['tag'])
        return success({
            "tag": args['tag']
        })
    except TagExistsException:
        raise RequestError(f"Tag already exists")

RenameTagArgs = TypedDict('RenameTagArgs', {
    'tag': str,
    'new_tag': str
})
@tag_api.route("/rename")
@exceptionWrapper
@args(RenameTagArgs)
def renameTag(args: RenameTagArgs):
    try:
        server.db.rename_tag(args['tag'], args['new_tag'])
        return success({
            "tag": args['tag'],
            "new_tag": args['new_tag']
        })
    except TagDoesNotExistException:
        raise RequestError(f"Unable to rename {args['tag']} to {args['new_tag']}, tag does not exist", 404)
    except TagExistsException:
        raise RequestError(f"Unable to rename {args['tag']} to {args['new_tag']}, tag already exists")


DeleteTagArgs = TypedDict('DeleteTagArgs', {
    'tag': str,
    'replacement': NotRequired[str]
})
@tag_api.route("/delete")
@exceptionWrapper
@args(DeleteTagArgs)
def deleteTag(args: DeleteTagArgs):
    try:
        server.db.delete_tag(args['tag'], args.get('replacement'))
        return success({
            "tag": args['tag'],
            "replacement": args.get('replacement')
        })
    except TagDoesNotExistException as e:
        raise RequestError(f"No such tag {e.tag}", 404)
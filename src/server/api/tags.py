from database import Database
from database.exceptions import TagExistsException, TagDoesNotExistException
from flask import Blueprint
from server.helpers import exceptionWrapper, success, args, RequestError, withDatabase
from typing import TypeVar
from typing_extensions import TypedDict, NotRequired

tag_api = Blueprint('tag_api', __name__, url_prefix='/tags')


@tag_api.route("/list")
@exceptionWrapper
@withDatabase
def listTags(db: Database):
    return success([x.as_object() for x in db.get_all_tags()])


GenericDict = TypeVar('GenericDict', bound=TypedDict)


class CreateTagArgs(TypedDict):
    tag: str


@tag_api.route("/create")
@exceptionWrapper
@args(CreateTagArgs)
@withDatabase
def createTag(db: Database, args: CreateTagArgs):
    # Attempt to create
    try:
        db.create_tag(args['tag'])
        return success({
            "tag": args['tag']
        })
    except TagExistsException:
        raise RequestError("Tag already exists")


RenameTagArgs = TypedDict('RenameTagArgs', {
    'tag': str,
    'new_tag': str
})


@tag_api.route("/rename")
@exceptionWrapper
@args(RenameTagArgs)
@withDatabase
def renameTag(db: Database, args: RenameTagArgs):
    try:
        db.rename_tag(args['tag'], args['new_tag'])
        return success({
            "tag": args['tag'],
            "new_tag": args['new_tag']
        })
    except TagDoesNotExistException:
        reason = "tag does not exist"
        code = 404
    except TagExistsException:
        reason = "tag already exists"
        code = 400
    raise RequestError(f"Unable to rename {args['tag']} to {args['new_tag']}, {reason}", code)


DeleteTagArgs = TypedDict('DeleteTagArgs', {
    'tag': str,
    'replacement': NotRequired[str]
})


@tag_api.route("/delete")
@exceptionWrapper
@args(DeleteTagArgs)
@withDatabase
def deleteTag(db: Database, args: DeleteTagArgs):
    try:
        db.delete_tag(args['tag'], args.get('replacement'))
        return success({
            "tag": args['tag'],
            "replacement": args.get('replacement')
        })
    except TagDoesNotExistException as e:
        raise RequestError(f"No such tag {e.tag}", 404)

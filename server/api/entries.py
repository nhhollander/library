from flask import Blueprint, Response, stream_with_context, send_file
from typing_extensions import TypedDict
from database.entry import EntryUpdateParams

from server.helpers import RequestError, exceptionWrapper, success, args, validate_tags
import server
import xdg.BaseDirectory  # type: ignore
from pathlib import Path
import hashlib
import os
import config
import magic

entry_api = Blueprint('entry_api', __name__, url_prefix='/entries')
mime = magic.Magic(mime=True)

GetEntryArgs = TypedDict('GetEntryArgs', {
    'id': str  # GET arguments can only be strings
})


@entry_api.route('/get')
@exceptionWrapper
@args(GetEntryArgs)
def getEntry(args: GetEntryArgs):
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError(f"Invalid ID {args['id']}: Not a number")
    entry = server.db.get_entry_by_id(id)
    if entry:
        return success(entry.object())
    else:
        raise RequestError(f"No such entry {id}", 404)


@entry_api.route("/create", methods=["POST"])
@exceptionWrapper
@args(EntryUpdateParams, 'POST')
def createEntry(args: EntryUpdateParams):
    # Validate input
    if 'tags' in args:
        validate_tags(args['tags'])
    # Construct new object
    entry = server.db.create_entry()
    entry.update_safe(args)
    return success({"entry_id": entry.id})


class UpdateEntryArgs(EntryUpdateParams):
    id: int


@entry_api.route("/update", methods=["POST"])
@exceptionWrapper
@args(UpdateEntryArgs, 'POST')
def updateEntry(args: UpdateEntryArgs):
    entry = server.db.get_entry_by_id(args['id'])
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    # Update modified fields
    entry.update_safe(args)


@entry_api.route('/preview')
@exceptionWrapper
@args(GetEntryArgs)
def getPreview(args: GetEntryArgs):
    """
    Attempt to return a preview image for this entry in accordance with the XDG thumbnail
    specification. https://specifications.freedesktop.org/thumbnail-spec/thumbnail-spec-latest.html
    """
    # Validate input and entry
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")
    entry = server.db.get_entry_by_id(id)
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    if not entry.storage_id:
        raise RequestError("Entry has no associated media", 404)
    # Get the thumbnail ID
    uri = Path(config.configuration['dataRoot'], entry.storage_id).as_uri()
    id = hashlib.md5(uri.encode()).hexdigest() + ".png"
    # Search for the thumbnail in the cache
    thumb_cache = Path(xdg.BaseDirectory.xdg_cache_home, "thumbnails")
    thumbnail_sizes = ['xx-large', 'x-large', 'large', 'normal']
    for thumb_size in thumbnail_sizes:
        thumb_path = Path(thumb_cache, thumb_size, id)
        if os.path.exists(thumb_path):
            return send_file(thumb_path)
            # with thumb_path.open("rb") as thumb:
            #     response = Response(thumb.read())
            #     response.headers['Content-Type'] = 'image/png'
            #     return response
    # TODO: Request thumbnails from Tumbler (via D-Bus)
    # TODO: Show a default image instead of returning json error
    raise RequestError(f"No preview available for entity {id}", 404)


@entry_api.route('/download')
@exceptionWrapper
@args(GetEntryArgs)
def download(args: GetEntryArgs):
    # Validate input and entry
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")
    entry = server.db.get_entry_by_id(id)
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    if not entry.storage_id:
        raise RequestError("Entry has no associated media", 404)
    # Return the data
    path = Path(config.configuration['dataRoot'], entry.storage_id)
    return send_file(path)

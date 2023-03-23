from flask import Blueprint, send_file  # type: ignore (PyLance mis-detected type of `path_or_file`)
from typing_extensions import TypedDict
from database.entry import EntryUpdateParams
from database.exceptions import DatabaseException

from server.helpers import RequestError, exceptionWrapper, success, args, withDatabase
import xdg.BaseDirectory  # type: ignore (Missing stub file)
from pathlib import Path
import hashlib
import os
import config
from database import Database
from util import mime as mime_util

entry_api = Blueprint('entry_api', __name__, url_prefix='/entries')

GetEntryArgs = TypedDict('GetEntryArgs', {
    'id': str  # GET arguments can only be strings
})


@entry_api.route('/get')
@exceptionWrapper
@args(GetEntryArgs)
@withDatabase
def getEntry(db: Database, args: GetEntryArgs):
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError(f"Invalid ID {args['id']}: Not a number")
    entry = db.get_entry_by_id(id)
    if entry:
        return success(entry.object())
    else:
        raise RequestError(f"No such entry {id}", 404)


@entry_api.route("/create", methods=["POST"])
@exceptionWrapper
@args(EntryUpdateParams, 'POST')
@withDatabase
def createEntry(db: Database, args: EntryUpdateParams):
    # Construct new object
    entry = db.create_entry()
    try:
        entry.update_safe(args)
    except DatabaseException as e:
        db.destroy_entry(entry)
        raise RequestError({'message': e.message})
    return success({"entry_id": entry.id})


class UpdateEntryArgs(EntryUpdateParams):
    id: int


@entry_api.route("/update", methods=["POST"])
@exceptionWrapper
@args(UpdateEntryArgs, 'POST')
@withDatabase
def updateEntry(db: Database, args: UpdateEntryArgs):
    entry = db.get_entry_by_id(args['id'])
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    # Update modified fields
    entry.update_safe(args)


@entry_api.route('/preview')
@exceptionWrapper
@args(GetEntryArgs)
@withDatabase
def getPreview(db: Database, args: GetEntryArgs):
    """
    Attempt to return a preview image for this entry in accordance with the XDG thumbnail
    specification. https://specifications.freedesktop.org/thumbnail-spec/thumbnail-spec-latest.html
    """
    # Validate input and entry
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")
    entry = db.get_entry_by_id(id)
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    if not entry.storage_id:
        raise RequestError("Entry has no associated media", 404)

    # Get the thumbnail ID
    file_path = Path(config.configuration['dataRoot'], entry.storage_id)
    thumb_id = hashlib.md5(file_path.as_uri().encode()).hexdigest() + ".png"

    # Attempt to find an existing preview image
    thumb_cache = Path(xdg.BaseDirectory.xdg_cache_home, "thumbnails")
    thumbnail_sizes = ['xx-large', 'x-large', 'large', 'normal']
    for thumb_size in thumbnail_sizes:
        thumb_path = Path(thumb_cache, thumb_size, thumb_id)
        if os.path.exists(thumb_path):
            return send_file(thumb_path)

    # TODO: Request thumbnails from Tumbler (via D-Bus)

    # Attempt to find a mime type icon
    icon = mime_util.find_icon_path(entry.mime_icon or '')
    if icon:
        return send_file(icon)

    raise RequestError(f"No preview available for entity {id}", 404)


class MimeIconArgs(TypedDict):
    mime: str


@entry_api.route('/mimeIcon')
@exceptionWrapper
@args(MimeIconArgs)
def getMimeIcon(args: MimeIconArgs):
    """
    Attempt to return an icon for the mime type of this object in accordance with the XDG icon
    specification.
    https://specifications.freedesktop.org/icon-theme-spec/icon-theme-spec-latest.html
    """

    icon = mime_util.find_icon_path(args['mime'])
    if icon:
        return send_file(icon)

    raise RequestError(f"Icon {args['mime']} unknown", 404)


@entry_api.route('/download')
@exceptionWrapper
@args(GetEntryArgs)
@withDatabase
def download(db: Database, args: GetEntryArgs):
    # Validate input and entry
    try:
        id = int(args['id'])
    except ValueError:
        raise RequestError("Invalid ID")
    entry = db.get_entry_by_id(id)
    if not entry:
        raise RequestError(f"No such entry {id}", 404)
    if not entry.storage_id:
        raise RequestError("Entry has no associated media", 404)
    # Return the data
    path = Path(config.configuration['dataRoot'], entry.storage_id)
    return send_file(path)

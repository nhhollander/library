from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.session import object_session
import time

from typing import cast, Any
import numpy as np

from database.types import EntryUpdateParams

from .base import Base
from .tag import Tag
from .db_utils import get_tag_ids, get_tag_id, encode_tags
from magic import Magic
from pathlib import Path
import config

from util import mime


class Entry(Base):
    __tablename__ = "entries"

    # List of fields that can be updated directly from an `EntryUpdateParams` object without
    # requiring any special translation, decoding, or validation
    __raw_update_fields: list[str] = ['item_name', 'storage_id', 'tags', 'description',
                                      'transcription', 'date_created', 'date_digitized', 'location']

    item_name: Mapped[str | None] = mapped_column(nullable=True)
    __storage_id: Mapped[str | None] = mapped_column(nullable=True, name='storage_id')
    tags_raw: Mapped[bytes] = mapped_column(default=b'', name='tags_raw')
    description:  Mapped[str | None] = mapped_column(nullable=True)
    transcription: Mapped[str | None] = mapped_column(nullable=True)
    date_created: Mapped[int] = mapped_column()
    date_digitized: Mapped[int] = mapped_column()
    date_indexed: Mapped[int] = mapped_column()
    date_modified: Mapped[int] = mapped_column()
    location: Mapped[str | None] = mapped_column(nullable=True)
    __mime_type: Mapped[str | None] = mapped_column(nullable=True, name='mime_type')
    __mime_icon: Mapped[str | None] = mapped_column(nullable=True, name='mime_icon')

    def __init__(self, **kw: dict[str, Any]):
        """
        Initialization wrapper. The `default` field in `mapped_column` corresponds with the
        `DEFAULT` parameter of a table's schema and therefore can only be set to a single static
        value at the time the database is created (or the schema updated). This initialization
        wrapper sets values to a dynamic default if they are not pre-initialized in `kw`.
        """
        def default(key: str, value: Any):
            if key not in kw:
                kw[key] = value
        default('date_created', time.time())
        default('date_digitized', time.time())
        default('date_indexed', time.time())
        default('date_modified', time.time())
        super().__init__(**kw)

    # =================== #
    # Getters and Setters #
    # =================== #

    @property
    def storage_id(self):
        """
        Gets the storage ID (simple access)
        """
        return self.__storage_id

    @storage_id.setter
    def storage_id(self, value: str):
        """
        Update the storage ID. Clears out mime type and icon values.
        """
        self.__storage_id = value
        self.__mime_type = None
        self.__mime_icon = None

    @property
    def mime_type(self):
        """
        Get the mime type of the entry. If the mime type is not known but a storage id is set,
        attempt to determine the mime type and save that info to the database.
        """
        # Validate request
        if self.__mime_type:
            return self.__mime_type
        if not self.storage_id:
            return None
        # Identify MIME
        magic = Magic(mime=True)
        path = Path(config.configuration['dataRoot'], self.storage_id)
        self.__mime_type = magic.from_file(path)
        return self.__mime_type

    @property
    def mime_icon(self):
        """
        Get the mime icon name for this entry.
        """
        # Validate request
        if self.__mime_icon:
            return self.__mime_icon
        if not self.__mime_type:
            return None
        # Identify icon
        icon = mime.find_icon_name(self.__mime_type)
        if not icon:
            return None
        return self.__mime_icon

    @property
    def tag_ids(self):
        """
        Get a list of tag IDs associated with this entry
        """
        return np.frombuffer(self.tags_raw, np.uint16).tolist()

    @property
    def tags(self):
        """
        Get the tags associated with this entity as strings.
        """
        tags = self.__session.query(Tag).filter(Tag.id.in_(self.tag_ids)).all()
        return [tag.name for tag in tags]

    @tags.setter
    def tags(self, tags: list[str] | list[int]):
        """
        Update the tags associated with this entity.
        """
        tag_ids: list[int]
        if isinstance(tags[0], str):
            session = self.__session
            tag_ids = get_tag_ids(session, cast(list[str], tags))
        else:
            tag_ids = cast(list[int], tags)
        self.tags_raw = encode_tags(tag_ids)

    # ================ #
    # Internal Helpers #
    # ================ #

    @property
    def __session(self):
        """
        Get the session associated with this object. Will raise an exception if this entry is not
        associated with any database, for example in the time between creating this entry and
        adding it to the database.
        """
        session = object_session(self)
        if not session:
            raise Exception("Unable to get session from orphaned entity")
        return session

    # ================ #
    # External Helpers #
    # ================ #

    def object(self):
        """Return an object representation of the entry object suitable for transmission"""
        keys = [
            "id", "item_name", "storage_id", "description", "transcription", "date_created",
            "date_digitized", "last_modified", "location", "tags", "mime_type", "mime_icon"
        ]
        data = {key: getattr(self, key) for key in keys}
        return data

    def add_tag(self, tag: str | int, commit: bool = True):
        """
        Add a tag to this entry.

        :param tag: Tag name or ID to assign to this entry.
        :param commit: Set to False to prevent the change from being automatically persisted
        """
        tag_id = get_tag_id(self.__session, tag) if isinstance(tag, str) else tag
        self.tags = self.tag_ids + [tag_id]

    def remove_tag(self, tag: str | int, commit: bool = True):
        """
        Remove a tag from this entry.

        :param tag: The name or ID of the tag to remove from this entry.
        :param commit: Set to False to prevent the change from being automatically persisted
        """
        tag_id = get_tag_id(self.__session, tag) if isinstance(tag, str) else tag
        tags = set(self.tag_ids)
        tags.remove(tag_id)
        self.tags = list(tags)

    def update_safe(self, params: EntryUpdateParams):
        """
        Validate and update options. If any of the given parameters are invalid, this method will
        fail without making any changes to the entry.
        """

        try:
            # Apply direct updates
            for field in self.__raw_update_fields:
                if field in params:
                    setattr(self, field, params[field])
        except Exception as e:
            # If any exception is encountered roll back the changes we just made
            self.__session.rollback()
            raise e

        # Commit!
        self.date_modified = int(time.time())
        self.__session.commit()

    def __repr__(self):
        return "Entry(" \
            f"id={self.id!r}, item_name={self.item_name!r}, storage_id={self.storage_id!r}, " \
            f"tags={self.tags!r}, description={self.description!r}, " \
            f"transcription={self.transcription!r}, date_created={self.date_created!r}, " \
            f"date_digitized={self.date_digitized!r}, date_indexed={self.date_digitized!r}, " \
            f"date_modified={self.date_modified!r}, location={self.location!r}" \
            ")"

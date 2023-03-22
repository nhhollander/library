from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.session import object_session
import time

from typing import cast, Any
import numpy as np

from database.types import EntryUpdateParams

from .base import Base
from .tag import Tag
from .db_utils import get_tag_ids, get_tag_id, encode_tags


class Entry(Base):
    __tablename__ = "entries"

    # List of fields that can be updated directly from an `EntryUpdateParams` object without
    # requiring any special translation, decoding, or special validation
    __raw_update_fields: list[str] = ['item_name', 'storage_id', 'description', 'transcription',
                                      'date_created', 'date_digitized', 'location']

    item_name: Mapped[str | None] = mapped_column(nullable=True)
    storage_id: Mapped[str | None] = mapped_column(nullable=True)
    tags_raw: Mapped[bytes] = mapped_column(default=b'')
    description:  Mapped[str | None] = mapped_column(nullable=True)
    transcription: Mapped[str | None] = mapped_column(nullable=True)
    date_created: Mapped[int] = mapped_column()
    date_digitized: Mapped[int] = mapped_column()
    date_indexed: Mapped[int] = mapped_column()
    date_modified: Mapped[int] = mapped_column()
    location: Mapped[str | None] = mapped_column(nullable=True)

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

    def object(self):
        """Return an object representation of the entry object suitable for transmission"""
        keys = [
            "id", "item_name", "storage_id", "description", "transcription", "date_created",
            "date_digitized", "last_modified", "location"
        ]
        data = {key: getattr(self, key) for key in keys}
        data['tags'] = self.get_tags()
        return data

    def get_tag_ids(self):
        return np.frombuffer(self.tags_raw, np.uint16).tolist()

    def get_tags(self) -> list[str]:
        tags = self.__session.query(Tag).filter(Tag.id.in_(self.get_tag_ids())).all()
        return [tag.name for tag in tags]

    def set_tags(self, tags: list[str] | list[int], commit: bool = True):
        """
        Set the tag list on this entry.

        :param tags: List of tags or tag IDs to assign to this entry.
        :param commit: Set to False to prevent the change from being automatically persisted
        """
        tag_ids: list[int]
        if isinstance(tags[0], str):
            session = self.__session
            tag_ids = get_tag_ids(session, cast(list[str], tags))
        else:
            tag_ids = cast(list[int], tags)
        self.tags_raw = encode_tags(tag_ids)
        if commit:
            self.__session.commit()

    def add_tag(self, tag: str | int, commit: bool = True):
        """
        Add a tag to this entry.

        :param tag: Tag name or ID to assign to this entry.
        :param commit: Set to False to prevent the change from being automatically persisted
        """
        tag_id = get_tag_id(self.__session, tag) if isinstance(tag, str) else tag
        self.set_tags(self.get_tag_ids() + [tag_id], commit)

    def remove_tag(self, tag: str | int, commit: bool = True):
        """
        Remove a tag from this entry.

        :param tag: The name or ID of the tag to remove from this entry.
        :param commit: Set to False to prevent the change from being automatically persisted
        """
        tag_id = get_tag_id(self.__session, tag) if isinstance(tag, str) else tag
        tags = set(self.get_tag_ids())
        tags.remove(tag_id)
        self.set_tags(list(tags), commit)

    def update_safe(self, params: EntryUpdateParams):
        """
        Validate and update options. If any of the given parameters are invalid, this method will
        fail without making any changes to the entry.
        """
        # Validate inputs
        tag_ids: list[int] = []
        if 'tags' in params:
            tag_ids = get_tag_ids(self.__session, params['tags'])

        # Apply updates that require translation
        if 'tags' in params:
            self.set_tags(tag_ids)
        # Apply direct updates
        for field in self.__raw_update_fields:
            if field in params:
                setattr(self, field, params[field])

        # Commit!
        self.date_modified = int(time.time())
        self.__session.commit()

    def __repr__(self):
        return "Entry(" \
            f"id={self.id!r}, item_name={self.item_name!r}, storage_id={self.storage_id!r}, " \
            f"tags={self.get_tags()!r}, description={self.description!r}, " \
            f"transcription={self.transcription!r}, date_created={self.date_created!r}, " \
            f"date_digitized={self.date_digitized!r}, date_indexed={self.date_digitized!r}, " \
            f"date_modified={self.date_modified!r}, location={self.location!r}" \
            ")"

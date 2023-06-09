from .base import Base
from .tag import TagIDListDecorator, TagList, Tag
from calendar import timegm
from database.types import EntryUpdateParams
from datetime import datetime, timezone, timedelta
from dateutil import parser
from magic import Magic
from pathlib import Path
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm.attributes import flag_modified
from typing import Any, Optional
from util import mime
import config
import traceback
from util.repr import repr_helper


__shared_parser = parser.parser()


class Entry(Base):
    __tablename__ = "entries"

    item_name: Mapped[str | None] = mapped_column(nullable=True)
    __storage_id: Mapped[str | None] = mapped_column(nullable=True, name='storage_id')
    tag_ids: Mapped[list[int]] = mapped_column(TagIDListDecorator, default=b'', name='tags')
    description:  Mapped[str | None] = mapped_column(nullable=True)
    transcription: Mapped[str | None] = mapped_column(nullable=True)
    date_created_raw: Mapped[int] = mapped_column(name='date_created')
    __date_created_tz: Mapped[int] = mapped_column(name='date_created_tz', default=0)
    date_digitized_raw: Mapped[int] = mapped_column(name='date_digitized')
    __date_digitized_tz: Mapped[int] = mapped_column(name='date_digitized_tz', default=0)
    date_indexed_raw: Mapped[int] = mapped_column(name='date_indexed')
    date_modified_raw: Mapped[int] = mapped_column(name='date_modified')
    location: Mapped[str | None] = mapped_column(nullable=True)
    __mime_type: Mapped[str | None] = mapped_column(nullable=True, name='mime_type')
    __mime_icon: Mapped[str | None] = mapped_column(nullable=True, name='mime_icon')
    size_raw: Mapped[int | None] = mapped_column(nullable=True, name='size')
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("entries.id"), name='parent')

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
        default('date_created', datetime.now())
        default('date_digitized', datetime.now())
        default('date_indexed', datetime.now())
        default('date_modified', datetime.now())
        default('tag_ids', [])
        super().__init__(**kw)

    # =================== #
    # Getters and Setters #
    # =================== #

    @property
    def storage_id(self):
        """Gets the storage ID. Nothing special to do here, but getter is required for setter"""
        return self.__storage_id

    @storage_id.setter
    def storage_id(self, value: str):
        """Update the storage ID. Clears out mime type and icon values."""
        self.__storage_id = value
        self.__mime_type = None
        self.__mime_icon = None
        self.size_raw = None

    @property
    def mime_type(self):
        """
        Get the mime type of the entry. If the mime type is not known but a storage id is set,
        attempt to determine the mime type and save that info to the database.
        """
        # Validate request
        if self.__mime_type:
            return self.__mime_type
        path = self.storage_path()
        if not path:
            return None
        # Identify MIME
        try:
            magic = Magic(mime=True)
            nested = self.__session.begin_nested()
            self.__mime_type = magic.from_file(path)
            nested.commit()
            return self.__mime_type
        except FileNotFoundError as e:
            traceback.print_exception(e)
            return ""

    @property
    def mime_icon(self):
        """Get the mime icon name for this entry."""
        # Validate request
        if self.__mime_icon:
            print(f"Mime icon for {self.id} is {self.__mime_icon}")
            return self.__mime_icon
        if not self.mime_type:
            print(f"No mime icon for {self.id}")
            return None
        # Identify icon
        print(f"Looking up icon for {self.id} with type {self.__mime_type}")
        icon = mime.find_icon_name(self.mime_type)
        if not icon:
            return None
        with self.__session.begin_nested():
            self.__mime_icon = icon
        return self.__mime_icon

    @property
    def tags(self):
        """Get the tags associated with this entity as strings."""
        return TagList(self.tag_ids, self.__session, lambda: flag_modified(self, 'tag_ids'))

    @tags.setter
    def tags(self, value: list[str] | list[Tag]):
        self.tags.update(value)

    @property
    def size(self):
        """Get the size of the item in bytes."""
        if self.size_raw:
            return self.size_raw
        path = self.storage_path()
        if not path:
            return None
        try:
            size = path.stat().st_size
            with self.__session.begin_nested():
                self.size_raw = size
            return size
        except Exception as e:
            traceback.print_exception(e)
            return 0

    @property
    def date_created(self):
        return self.__dt_from_unix(self.date_created_raw, self.__date_created_tz)

    @date_created.setter
    def date_created(self, dt: datetime | str):
        self.date_created_raw, self.__date_created_tz = self.__dt_to_unix(dt)

    @property
    def date_digitized(self):
        return self.__dt_from_unix(self.date_digitized_raw, self.__date_digitized_tz)

    @date_digitized.setter
    def date_digitized(self, dt: datetime | str):
        self.date_digitized_raw, self.__date_digitized_tz = self.__dt_to_unix(dt)

    @property
    def date_indexed(self):
        return self.__dt_from_unix(self.date_indexed_raw, 0)

    @date_indexed.setter
    def date_indexed(self, dt: datetime | str):
        self.date_indexed_raw, _ = self.__dt_to_unix(dt)

    @property
    def date_modified(self):
        return self.__dt_from_unix(self.date_modified_raw, 0)

    @date_modified.setter
    def date_modified(self, dt: datetime | str):
        self.date_modified_raw, _ = self.__dt_to_unix(dt)

    @property
    def parent(self) -> Optional["Entry"]:
        query = select(Entry).where(Entry.id == self.parent_id)
        result = self.__session.execute(query).one_or_none()
        return result[0] if result else None

    @property
    def children(self) -> list["Entry"]:
        query = select(Entry).where(Entry.parent_id == self.id)
        result = self.__session.execute(query).all()
        return [x[0] for x in result]

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

    def __dt_to_unix(self, dt: datetime | str) -> tuple[int, int]:
        """Convert a datetime object into a utc timestamp and timezone offset value."""
        if isinstance(dt, str):
            dt = __shared_parser.parse(dt)
        offset: int = 0
        if dt.tzinfo:
            tz = dt.tzinfo.utcoffset(None)
            if tz:
                offset = int(tz.total_seconds())
        return timegm(dt.utctimetuple()), offset

    def __dt_from_unix(self, unix_time: int, tz_offset: int):
        """Convert a unix timestamp and timezone offset into a datetime object."""
        tz = timezone(timedelta(seconds=tz_offset))
        return datetime.fromtimestamp(unix_time, tz=tz)

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

    def update_safe(self, params: EntryUpdateParams):
        """
        Validate and update options. If any of the given parameters are invalid, this method will
        fail without making any changes to the entry.
        """

        try:
            # Apply direct updates
            for field in getattr(EntryUpdateParams, '__optional_keys__'):
                if field in params:
                    # Avoid triggering update actions unnecessarily
                    if not getattr(self, field) == params[field]:
                        setattr(self, field, params[field])
        except Exception as e:
            # If any exception is encountered roll back the changes we just made
            self.__session.rollback()
            raise e

        # Commit!
        self.date_modified = datetime.now().astimezone()
        self.__session.commit()

    def storage_path(self):
        """
        Return the computed path to the entry on disk. This function does not guarantee that the
        path points to an actual file.
        """
        if not self.storage_id:
            return None
        return Path(config.configuration['dataRoot'], self.storage_id)

    def __repr__(self):
        return repr_helper(self, ['id', 'item_name', '__storage_id', 'tag_ids', 'tags',
                                  'description', 'transcription', 'date_created_raw',
                                  '__date_created_tz', 'date_digitized_raw',
                                  '__date_digitized_tz', 'date_indexed_raw', 'date_modified_raw',
                                  'location', '__mime_type', '__mime_icon', 'size_raw'])

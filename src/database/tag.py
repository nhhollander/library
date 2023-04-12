from sqlalchemy import Dialect

from database.exceptions import InvalidTagException
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.sql import select, func
from sqlalchemy.types import TypeDecorator, BLOB
from sqlalchemy.exc import NoResultFound
from typing import Optional, SupportsIndex, cast, Callable
import numpy as np

from util.repr import repr_helper

_TAG_TYPE = np.uint16


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str]
    count: Mapped[int] = mapped_column(default=0)

    def as_object(self):
        """Convert the tag into a transmissible object."""
        obj_fields = ['name', 'count']
        return {key: getattr(self, key) for key in obj_fields}

    def __repr__(self):
        return repr_helper(self, ["id", "name", "count"])


class TagIDListDecorator(TypeDecorator[list[int]]):
    """Decorator for automatically expanding a packed byte list into a list of tag IDs"""

    impl = BLOB
    cache_ok = True

    def process_bind_param(self, value: Optional[list[int]], dialect: Dialect) -> Optional[bytes]:
        if value is None:
            return None
        return np.array(value, _TAG_TYPE).tobytes()

    def process_result_value(self, value: Optional[bytes], dialect: Dialect) -> Optional[list[int]]:
        if value is None:
            return None
        return np.frombuffer(value, _TAG_TYPE).tolist()


class TagList():

    __id_list: list[int]
    __session: Session
    __mark_dirty: Callable[[], None]

    def __init__(self, id_list: list[int], session: Session, mark_dirty: Callable[[], None]):
        """
        Create a new TagList object.

        The `mark_dirty` function is required because SQLAlchemy can not automatically detect when
        a list type database field has been appended to or removed from.

        :param id_list: Reference to the array storing the decoded tag list.
        :param session: Session object to use for nested transactions and tag lookups.
        :param mark_dirty: Function to mark the id_list column as modified.
        """
        self.__id_list = id_list
        self.__session = session
        self.__mark_dirty = mark_dirty

    # ================== #
    # Set Implementation #
    # ================== #

    def add(self, tag: Tag | str):
        """
        Append a new tag to the tag list. If the tag is already present in the list, this method has
        no effect.

        :param tag: Tag object or name to add to the list.
        :raises InvalidTagException: If the `tag` parameter is a string that can not be resolved to
            a tag object.
        """
        if isinstance(tag, str):
            tag = get_tag(self.__session, tag)
        if tag.id in self.__id_list:
            return
        with self.__session.begin_nested():
            self.__id_list.append(tag.id)
            tag.count += 1
            self.__mark_dirty()

    def remove(self, tag: Tag | str):
        """
        Remove a tag from the tag list.

        :param tag: Tag object or name to add to the list.
        :raises InvalidTagException: If the `tag` parameter is a string that can not be resolved to
            a Tag object.
        :raises KeyError: If the tag is not present in the list.
        """
        if isinstance(tag, str):
            tag = get_tag(self.__session, tag)
        if tag.id not in self.__id_list:
            raise KeyError(tag)
        with self.__session.begin_nested():
            self.__id_list.remove(tag.id)
            tag.count -= 1
            self.__mark_dirty()

    def replace(self, old_tag: Tag | str, new_tag: Tag | str):
        """
        Replace one tag with another tag in this list. If the new tag is already present in this
        list this function has no effect.

        Known Bug: If two invalid strings are passed to this function the raised
        `InvalidTagException` will only include the first tag.

        :param old_tag: Existing tag to be replaced.
        :param new_tag: Tag to replace the existing tag with.
        :raises InvalidTagException: If the new and/or old tags are specified as a string that can
            not be resolved to a Tag object(s).
        :raises KeyError: If the old tag is not present in this list.
        """
        if isinstance(old_tag, str):
            old_tag = get_tag(self.__session, old_tag)
        if isinstance(new_tag, str):
            new_tag = get_tag(self.__session, new_tag)
        if old_tag.id not in self.__id_list:
            raise KeyError(old_tag)
        self.remove(old_tag)
        self.add(new_tag)

    # ======================== #
    # Container Implementation #
    # ======================== #

    def __len__(self):
        return len(self.__id_list)

    def __getitem__(self, x: SupportsIndex | slice) -> list[Tag]:
        ids = self.__id_list[x]
        if isinstance(ids, int):
            ids = [ids]
        return [x[0] for x in self.__session.execute(select(Tag).where(Tag.id.in_(ids))).all()]

    # __setitem__ not supported (use `add`)
    # __delitem__ not supported (use `remove)

    def __iter__(self):
        for item in self.all():
            yield item

    def __reversed__(self):
        for item in reversed(self.all()):
            yield item

    def __contains__(self, item: Tag | str):
        if isinstance(item, str):
            item = get_tag(self.__session, item)
        return item.id in self.__id_list

    # ================ #
    # External Helpers #
    # ================ #

    def all(self):
        """Return all of the tags in this list as `Tag` objects."""
        return self[0:len(self.__id_list)]

    def joined(self):
        """Return a stringified tag list separated by spaces."""
        return ' '.join((x.name for x in self))

    def update(self, tags: list[Tag] | list[str]):
        """
        Update the tag list to a set of new values. This helper method takes a list of tags and
        determines which tags to add/remove from the list. If the new tag list is identical to the
        old tag list, this function has no effect.

        :param tags: List of tags.
        :raises InvalidTagException: If the tags parameter is a list of strings and any of the tags
            can not be resolved to `Tag` objects.
        """
        if isinstance(tags[0], str):
            tags = get_tags(self.__session, cast(list[str], tags))
        tags = cast(list[Tag], tags)

        incoming = set(tags)
        existing = set(self.all())
        new_tags = incoming - existing
        deleted_tags = existing - incoming
        print(f"Updating tags: added {new_tags} removed {deleted_tags}")
        for tag in new_tags:
            self.add(tag)
        for tag in deleted_tags:
            self.remove(tag)


def get_tag(session: Session, tag: str) -> Tag:
    """
    Resolve a tag name to a tag object.

    :param tag: Tag name to resolve.
    :raises InvalidTagException: If the tag name can not be resolved.
    :returns: A tag object.
    """
    try:
        return session.execute(select(Tag).where(Tag.name == tag)).one()[0]
    except NoResultFound:
        raise InvalidTagException([tag])


def get_tags(session: Session, tags: list[str]) -> list[Tag]:
    """
    Resolve a list of tag names to a list of tag objects.

    :param tag: List of tag names to resolve.
    :raises InvalidTagException: If any of the tag names can not be resolved.
    :returns: A list of tag objects.
    """
    tags_deduplicated = set(tags)
    result = session.execute(select(Tag).where(Tag.name.in_(tags_deduplicated))).all()
    result_tags = [x.tuple()[0] for x in result]
    if len(result_tags) != len(tags_deduplicated):
        bad_tags = tags_deduplicated - set([x.name for x in result_tags])
        raise InvalidTagException(list(bad_tags))
    return result_tags


def tag_exists(session: Session, tag: str) -> bool:
    """
    Check if the requested tag exists.

    :param tag: Tag name to check.
    :returns: `True` if the tag exists.
    """
    return session.execute(select(func.count(Tag)).where(Tag.name == tag)).scalar() == 1


def get_tag_ids_multiple(session: Session, tags: list[list[str]]) -> list[bytes]:
    """
    This function returns tag IDs from multiple sets of tags.

    :param session: Database session to retrieve tag information from
    :param tags: List of lists of tags to convert.
    :raises InvalidTagException: If any of the requested tags do not exist.
    :returns: A list of lists of tag IDs
    """
    bad_tags: list[str] = []
    result: list[bytes] = []
    for t in tags:
        query_result = session.execute(select(Tag.id, Tag.name).where(Tag.name.in_(t))).all()
        if len(query_result) != len(t):
            bad_tags.extend(set(t) - set([tag[1] for tag in query_result]))
        result.append(np.array([tag[0] for tag in query_result], _TAG_TYPE).tobytes())
    if len(bad_tags) > 0:
        raise InvalidTagException(bad_tags)
    return result

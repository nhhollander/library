from sqlalchemy import Engine, create_engine, func, event
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.exc import NoResultFound

from typing import ParamSpec, TypeVar
from database.dbstat import DBStat

from database.exceptions import InvalidTagException, TagDoesNotExistException, TagExistsException
from util.timer import Timer

from .base import Base
from .tag import Tag
from .entry import Entry
from .types import SearchParameters
from .db_utils import decode_tags, get_tag_ids, encode_tags, get_tag_ids_multiple
from .functions import register

# Register the custom function manager
event.listen(Engine, "connect", register)

DEFAULT_POST_LIMIT = 50
PAGE_SIZE_LIMIT = 500

P = ParamSpec('P')
R = TypeVar('R')


class Database:

    __engine: Engine
    __scoped_session: scoped_session[Session]

    def __init__(self, path: str = ""):
        """
        Initialize a new Database wrapper.

        This constructor can be used in two ways, to initialize a new database connection, or to
        wrap an existing session object (Such as one generated from Flash's Sqlalchemy extension).

        To initialize a new connection, leave the `session` object as `None` and optionally specify
        a `path` to the database file. Leave this parameter as an empty string to initialize around
        an in-memory database.

        To wrap an existing connection, set the `session` object to the session generated by
        whichever database utility you are using. The `path` argument is ignored in this case.

        :param path: Path to the database file. Only used for new connections.
        :param session: Existing session object to wrap.
        """
        self.__engine = create_engine(f"sqlite://{path}", echo=False)
        self.__scoped_session = scoped_session(sessionmaker(bind=self.__engine))

        Base.metadata.create_all(self.__engine)

        self.commit()

    # =================== #
    #  General Functions  #
    # =================== #

    def commit(self):
        """Write changes to the database."""
        self.__session.commit()

    def rollback(self):
        """Abandon all pending changes."""
        self.__session.rollback()

    def release(self):
        """
        Release any open session objects. SQLite has a limited pool of session objects. Although
        sessions are automatically released back to the pool when they are reaped by the garbage
        collector, python makes no guarantees about when the garbage collector will run, causing
        dangling sessions to last for an unspecified amount of time.

        An alternative to this method would be to call `.close()` on the session object once you are
        finished with it, or use the `with session:` syntax to automatically close it at the end of
        a scope.

        Note: Calling this function will invalidate all database resources that were created using
        the active session. For example, if you execute a query that returns several `Entry` objects
        and then call this function , those `Entry` objects will be invalid and will likely cause
        a runtime exception if used.
        """
        self.__scoped_session.remove()

    @property
    def __session(self):
        return self.__scoped_session()

    def total_size(self):
        """
        Return the total size in bytes of all entries in the engine. This will not trigger a size
        re-calculation for entries which do not have this value cached.
        """
        return sum([x[0] or 0 for x in self.__session.query(Entry.size_raw).all()])

    def entry_count(self):
        """
        Return the number of entries tracked in the database.
        """
        return self.__session.query(Entry.id).count()

    def database_size(self):
        """
        Get the number of bytes used by the database.

        Note: It is possible that the actual database could be larger than the size reported by
        this method because of extraneous data which has not yet been discarded by a `VACUUM`
        command.
        """
        dbstat_tables = self.__session.query(DBStat.pgsize).all()
        return sum([x[0] for x in dbstat_tables])

    # ================= #
    #  Query Functions  #
    # ================= #

    def tag_query(self, tags: list[str], forbidden: list[str] = []):
        """
        Query the database for Entries which match all required tags, and optionally possess none
        of the forbidden tags.

        :param tags: List of tags to search for
        :param forbidden: List of tags to exclude from results
        :returns: A list of matching entries plus information on invalid tags
        """
        tag_ids, forbidden_ids = get_tag_ids_multiple(self.__session, [tags, forbidden])
        filter = func.check_tags(Entry.tags_raw, encode_tags(tag_ids), encode_tags(forbidden_ids))
        result = self.__session.query(Entry).filter(filter).all()
        return result

    def search(self, params: SearchParameters):
        """
        Perform a search of the database.
        """
        query = self.__session.query(Entry)
        # Parse the tag components
        tag_str = params.get('tags', [])
        f_tag_str = params.get('f_tags', [])
        tag_ids, forbidden_ids = get_tag_ids_multiple(self.__session, [tag_str, f_tag_str])
        tags_enc = encode_tags(tag_ids)
        f_tags_enc = encode_tags(forbidden_ids)
        query = query.filter(func.check_tags(Entry.tags_raw, tags_enc, f_tags_enc))

        # Time ranges
        if 'since' in params:
            query.filter(Entry.date_created_raw >= params['since'])
        if 'until' in params:
            query.filter(Entry.date_created_raw <= params['until'])
        if 'since_modified' in params:
            query.filter(Entry.date_modified_raw >= params['since_modified'])
        if 'until_modified' in params:
            query.filter(Entry.date_modified_raw <= params['until_modified'])
        if 'since_digitized' in params:
            query.filter(Entry.date_digitized_raw >= params['since_digitized'])
        if 'until_digitized' in params:
            query.filter(Entry.date_digitized_raw <= params['until_digitized'])
        if 'since_indexed' in params:
            query.filter(Entry.date_indexed_raw >= params['since_indexed'])
        if 'until_indexed' in params:
            query.filter(Entry.date_indexed_raw <= params['until_indexed'])

        # Quantity and Page
        page_size = min(max(0, params.get('count', DEFAULT_POST_LIMIT)), PAGE_SIZE_LIMIT)
        offset = page_size * params.get('page', 0)
        query = query.limit(page_size)
        query = query.offset(offset)

        return query.all()

    # ================ #
    #  Tag Management  #
    # ================ #

    def get_all_tags(self):
        """Retrieve a list of all tags known to the database."""
        return self.__session.query(Tag).all()

    def tag_exists(self, tag: str):
        return self.__session.query(Tag).filter(Tag.name == tag).count() > 0

    def check_tags(self, tags: list[str]) -> list[str]:
        """
        Make sure all tags exist returning a list of invalid tags.

        Note: Because this method returns a list of invalid tags, `if check_tags(['invalid']):` will
        evaluate as True.

        :param tags: List of tags to verify
        :return: A list of invalid tags
        """
        try:
            get_tag_ids(self.__session, tags)
            return []
        except InvalidTagException as e:
            return e.tags

    def create_tag(self, tag: str):
        """
        Register a new tag in the database. If the tag already exists, an exception will be raised.

        :param tag: The tag name to create.
        """
        if self.tag_exists(tag):
            raise TagExistsException(tag)
        newTag = Tag(name=tag)
        self.__session.add(newTag)
        self.commit()

    def delete_tag(self, tag: str, new_tag_name: str | None = None):
        """
        Remove a tag from the database and deletes it from all entries, optionally replacing it
        with the new tag.

        :param tag: The tag to delete
        :param new_tag: The optional tag to replace all instance of `tag` with
        """
        try:
            old_tag = self.__session.query(Tag).filter(Tag.name == tag).one()
        except NoResultFound:
            raise TagDoesNotExistException(tag)
        new_tag = self.__session.query(Tag).filter(Tag.name == new_tag_name).one_or_none()
        if new_tag:
            new_tag.count += old_tag.count
        affected_entries = self.__session \
            .query(Entry).filter(func.has_tag(Entry.tags_raw, old_tag.id)).all()
        for entry in affected_entries:
            if new_tag:
                entry.replace_tag(old_tag.id, new_tag.id)
            else:
                entry.remove_tag(old_tag.id)
        self.__session.delete(old_tag)
        self.commit()

    def rename_tag(self, tag: str, new_tag: str):
        """
        Rename an existing tag. All entries will refer to this new name.

        :param tag: The old tag name
        :param new_tag: The new tag name
        """
        try:
            tag_object = self.__session.query(Tag).where(Tag.name == tag).one()
        except NoResultFound:
            raise TagDoesNotExistException(tag)
        if self.tag_exists(new_tag):
            raise TagExistsException(new_tag)
        tag_object.name = new_tag
        self.commit()

    def update_tag_counts(self):
        """
        Iterate over the database and collect updated tag counts. This is a pretty expensive query
        to run and should only be used to repair the database after tags have been manually
        adjusted or other changes have been made that requires a full recalculation.

        :returns: A tuple containing the number of tags updated and the amount of time it took.
        """
        timer = Timer()
        print("Starting tag update")
        tag_map: dict[int, Tag] = {}
        for tag in self.__session.query(Tag).all():
            tag_map[tag.id] = tag
            tag.count = 0
        print(f"Sorted tag objects in {timer.time_formatted()}, starting count")
        timer.lap()
        for entry_id, raw_tags in self.__session.query(Entry.id, Entry.tags_raw).all():
            for id in decode_tags(raw_tags):
                if id not in tag_map:
                    print(f"Entry {entry_id} contains invalid tag {id}")
                else:
                    tag_map[id].count += 1
        print(f"Counted tags in {timer.time_formatted(True)} (total {timer.time_formatted()}), "
              "saving changes")
        timer.lap()
        self.__session.commit()
        print(f"Changes saved in {timer.time_formatted(True)} (total {timer.time_formatted()})")
        return len(tag_map), timer.get_time()

    # ================== #
    #  Entry Management  #
    # ================== #

    def create_entry(self):
        """
        Create and return a new entry.

        This helper method ensures that the entry is initialized and inserted into the database
        (weird stuff happens if you try to operate on an uninitialized entry). Automatic commit can
        not be disabled on this function to prevent the user from accessing an uninitialized entry
        object.

        :returns: A new Entry
        """
        entry = Entry()
        self.__session.add(entry)
        return entry

    def destroy_entry(self, entry: Entry):
        """
        Destroy an entry.
        """
        self.__session.delete(entry)

    def get_entry_by_id(self, id: int) -> Entry | None:
        """
        Get an entry by ID value.

        :param id: Entry id number.
        :returns: The identified entry or None if it does not exist.
        """
        entries = self.__session.query(Entry).where(Entry.id == id).all()
        return entries[0] if len(entries) > 0 else None

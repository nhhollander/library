# cspell:ignore pageno, pagetype, ncell, pgoffset
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from util.repr import repr_helper


class Base(DeclarativeBase):
    pass


class DBStat(Base):
    """
    In SQLite, dbstat represents a special virtual table which contains statistical information
    about the database.
    The schema for this database can be found at https://www.sqlite.org/dbstat.html.
    """
    __tablename__ = "dbstat"

    name: Mapped[str] = mapped_column()
    path: Mapped[str] = mapped_column()
    pageno: Mapped[int] = mapped_column(primary_key=True)
    pagetype: Mapped[str] = mapped_column()
    ncell: Mapped[int] = mapped_column()
    payload: Mapped[int] = mapped_column()
    unused: Mapped[int] = mapped_column()
    mx_payload: Mapped[int] = mapped_column()
    pgoffset: Mapped[int] = mapped_column()
    pgsize: Mapped[int] = mapped_column()

    def __repr__(self) -> str:
        return repr_helper(self, ['name', 'path', 'pageno', 'pagetype', 'ncell', 'payload',
                                  'unused', 'mx_payload', 'pgoffset', 'pgsize'])

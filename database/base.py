from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """
    Base class for all database entries. The `id` column is an INTEGER PRIMARY KEY which acts as an
    alias for the internal `rowid` column. https://www.sqlite.org/rowidtable.html
    """
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, nullable=False)

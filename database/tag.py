from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str]
    post_count: Mapped[int] = mapped_column(default=0)

    def __repr__(self):
        return f"Tag(id={self.id!r}, name={self.name!r})"

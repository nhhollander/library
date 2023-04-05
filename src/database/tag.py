from .base import Base
from sqlalchemy.orm import Mapped, mapped_column


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str]
    count: Mapped[int] = mapped_column(default=0)

    def as_object(self):
        """Convert the tag into a transmissible object."""
        obj_fields = ['name', 'count']
        return {key: getattr(self, key) for key in obj_fields}

    def __repr__(self):
        return f"Tag(id={self.id!r}, name={self.name!r})"
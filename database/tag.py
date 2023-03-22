from sqlalchemy.orm import Mapped
from .base import Base

class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str]

    def __repr__(self):
        return f"Tag(id={self.id!r}, name={self.name!r})"

class DatabaseException(Exception):
    """
    Base exception from which all other database specific exceptions should inherit.
    """
    message: str


class TagExistsException(DatabaseException):

    def __init__(self, tag: str):
        self.message = f"Tag {tag} already exists"
        self.tag = tag
        self.args = (self.message, tag)


class TagDoesNotExistException(DatabaseException):

    def __init__(self, tag: str):
        self.message = f"Tag {tag} does not exist"
        self.tag = tag
        self.args = (self.message, tag)


class InvalidTagException(DatabaseException):

    def __init__(self, tags: list[str]):
        self.message = f"Invalid tag{'s' if len(tags) > 1 else ''}: {tags}"
        self.tags = tags
        self.args = (self.message, tags)

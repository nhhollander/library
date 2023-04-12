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
    """
    Represents one or more tags which have been requested but do not exist in the database.
    """
    def __init__(self, tags: list[str]):
        if len(tags) > 1:
            self.message = f"Invalid tags: {tags}"
        elif len(tags) == 1:
            self.message = f"Invalid tag: {tags[0]}"
        else:
            raise ValueError("Invalid tag exception raised with no invalid tags specified")
        self.tags = tags
        self.args = (self.message, tags)

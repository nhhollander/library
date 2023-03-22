from typing import List


class TagExistsException(Exception):

    def __init__(self, tag: str):
        self.message = f"Tag {tag} already exists"
        self.tag = tag
        self.args = (self.message, tag)


class TagDoesNotExistException(Exception):

    def __init__(self, tag: str):
        self.message = f"Tag {tag} does not exist"
        self.tag = tag
        self.args = (self.message, tag)


class InvalidTagException(Exception):

    def __init__(self, tags: List[str]):
        self.message = f"Invalid tag{'s' if len(tags) > 0 else ''}: {tags}"
        self.tags = tags
        self.args = (self.message, tags)

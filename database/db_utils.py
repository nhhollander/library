##
# This file contains common utilities for interacting with the database that are not specific to
# any specific component of the index. Type imports are kind of weird to avoid issues with circular
# dependencies

from sqlalchemy.orm import Session
import numpy as np
from typing import List

from database.exceptions import InvalidTagException


def get_tag_id(session: Session, tag: str):
    """Get the numeric ID of a single tag"""
    from .tag import Tag
    result = session.query(Tag).filter(Tag.name == tag).all()
    if len(result) == 0:
        raise InvalidTagException([tag])
    return result[0].id


def get_tag_ids(session: Session, tags: List[str]):
    """
    Resolve a list of tags to a list of tag IDs.

    :param session: Database session to retrieve tag information from
    :param tags: List of tags to convert.
    :returns: A list of tag IDs
    """
    from .tag import Tag
    result = session.query(Tag).filter(Tag.name.in_(tags)).all()
    if len(result) != len(tags):
        invalid_tags = list(set(tags) - set([tag.name for tag in result]))
        raise InvalidTagException(invalid_tags)
    return [tag.id for tag in result]


def get_tag_ids_multiple(session: Session, tags: List[List[str]]) -> List[List[int]]:
    """
    This function operates similar to `get_tag_ids` but returns multiple separate lists of tag ids
    only throwing a single exception for all of the lists.

    :param session: Database session to retrieve tag information from
    :param tags: List of lists of tags to convert.
    :returns: A list of lists of tag IDs
    """
    bad_tags: List[str] = []
    result: List[List[int]] = []
    for t in tags:
        try:
            result.append(get_tag_ids(session, t))
        except InvalidTagException as e:
            bad_tags.extend(e.tags)
    if len(bad_tags) > 0:
        raise InvalidTagException(bad_tags)
    return result


def encode_tags(tags: List[int]):
    """
    Convert a list of tag IDs into a 16 bit encoded array.
    """
    return np.array(tags, np.uint16).tobytes()

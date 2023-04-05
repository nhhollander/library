from datetime import datetime
from typing_extensions import TypedDict, NotRequired


class SearchParameters(TypedDict):
    """
    Represents the raw parameters that can be used in a general search query.

    :param tags: List of tags which must be present.
    :param f_tags: List of tags which must not be present (forbidden).
    :param since: `date_created` must be greater than or equal to.
    :param until: `date_created` must be less than or equal to.
    :param since_modified: `date_modified` must be greater than or equal to.
    :param until_modified: `date_modified` must be less than or equal to.
    :param since_digitized: `date_digitized` must be greater than or equal to.
    :param until_digitized: `date_digitized` must be less than or equal to.
    :param since_indexed: `date_indexed` must be greater than or equal to.
    :param until_indexed: `date_indexed` must be less than or equal to.
    :param count: Number of posts to return.
    :param page: Page number to return.
    """
    tags: NotRequired[list[str]]
    f_tags: NotRequired[list[str]]
    since: NotRequired[int]
    until: NotRequired[int]
    since_modified: NotRequired[int]
    until_modified: NotRequired[int]
    since_digitized: NotRequired[int]
    until_digitized: NotRequired[int]
    since_indexed: NotRequired[int]
    until_indexed: NotRequired[int]
    count: NotRequired[int]
    page: NotRequired[int]


class EntryUpdateParams(TypedDict):
    """
    Typed dictionary of user-updatable entry parameters.
    """
    item_name: NotRequired[str]
    storage_id: NotRequired[str]
    tags: NotRequired[list[str]]
    description: NotRequired[str | None]
    transcription: NotRequired[str | None]
    date_created: NotRequired[datetime | str]
    date_digitized: NotRequired[datetime | str]
    location: NotRequired[str | None]

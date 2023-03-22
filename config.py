import json
import pathlib
from typing_extensions import TypedDict


class ConfigType(TypedDict):
    dataRoot: str


__directory = pathlib.Path(__file__).parent.absolute()
with pathlib.Path(__directory, "config.json").open() as conf:
    configuration: ConfigType = json.load(conf)

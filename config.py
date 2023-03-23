import json
import pathlib

__directory = pathlib.Path(__file__).parent.absolute()
with pathlib.Path(__directory, "config.json").open() as conf:
    configuration = json.load(conf)

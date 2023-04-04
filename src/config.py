import json
from pathlib import Path

__directory = Path(__file__).parent.parent.absolute()
with Path(__directory, "config.json").open() as conf:
    configuration = json.load(conf)

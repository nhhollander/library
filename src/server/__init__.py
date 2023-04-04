from flask import Flask

from database import Database
from .api import api
from .site import site
from pathlib import Path

root = Path(__file__).parent.parent.parent
# TODO: Remove `str()` once https://github.com/pallets/flask/pull/4921 is available in pip
template_dir = str(Path(root, "res/templates").resolve())
static_dir = Path(root, "res/static").resolve()

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
__db = Database("/local.db")

app.register_blueprint(api)
app.register_blueprint(site)


def get_db_internal():
    """
    Retrieve a handle to the database object. Normally you should obtain a handle to this object
    by decorating your function with the `withDatabase` decorator defined in helpers.py, as it will
    ensure that your session is committed and cleaned up at the end of the transaction.
    """
    return __db

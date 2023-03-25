from flask import Flask

from database import Database
from .api import api
from .site import site

app = Flask(__name__)
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

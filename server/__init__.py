from flask import Flask

from database import Database
from .api import api
from .site import site

app = Flask(__name__)
db = Database("/local.db")

app.register_blueprint(api)
app.register_blueprint(site)

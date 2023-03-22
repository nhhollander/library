from flask import Blueprint
from .tags import tag_api
from .entries import entry_api
from .debug import debug_api

api = Blueprint('api', __name__, url_prefix='/api')
api.register_blueprint(tag_api)
api.register_blueprint(entry_api)
api.register_blueprint(debug_api)

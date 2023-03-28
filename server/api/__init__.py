from flask import Blueprint
from .tags import tag_api
from .entries import entry_api
from .admin import admin_api

api = Blueprint('api', __name__, url_prefix='/api')
api.register_blueprint(tag_api)
api.register_blueprint(entry_api)
api.register_blueprint(admin_api)

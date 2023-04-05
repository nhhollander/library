from .admin import admin_api
from .entries import entry_api
from .tags import tag_api
from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api')
api.register_blueprint(tag_api)
api.register_blueprint(entry_api)
api.register_blueprint(admin_api)

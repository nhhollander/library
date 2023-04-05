from .credits import credits
from .entry import entry, edit_entry
from .index import index
from .search import search
from .tags import tags
from .upload import upload
from flask import Blueprint

site = Blueprint('site', __name__)

site.add_url_rule('/', '/', index)
site.add_url_rule('/credits', '/credits', credits)
site.add_url_rule('/tags', '/tags', tags)
site.add_url_rule('/entry', '/entry', entry)
site.add_url_rule('/editEntry', '/editEntry', edit_entry, methods=['GET', 'POST'])
site.add_url_rule('/upload', '/upload', upload, methods=['GET', 'POST'])
site.add_url_rule('/search', '/search', search)

from flask import Blueprint
from database import Database

from server.helpers import exceptionWrapper, success, withDatabase

admin_api = Blueprint("admin_api", __name__, url_prefix="/admin")


@admin_api.route("/recalculateTagCounts")
@exceptionWrapper
@withDatabase
def recalculateTagCounts(db: Database):
    count, time = db.update_tag_counts()
    return success({
        "tags_updated": count,
        "time": time
    })

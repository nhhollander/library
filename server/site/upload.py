from server.helpers import exceptionWrapper, templateWrapper, withDatabase
from server.helpers import StandardRenderParams
from database import Database
from flask import request, redirect
from .entry import handle_entry_update


class UploadParams(StandardRenderParams):
    stale_error: dict[str, str]


@exceptionWrapper
@withDatabase
@templateWrapper
def upload(db: Database):
    render_params: UploadParams = {
        'messages': [],
        'stale_error': {}
    }

    if request.method == "POST":
        # Create a new entry
        entry = db.create_entry()
        message = handle_entry_update(db, entry)
        if message:
            render_params['messages'].append(message)
            # Populate input values back to the page so the user doesn't lose their data
            render_params['stale_error'] = request.form
        else:
            return redirect(f"/entry?id={entry.id}", code=303)

    return 'upload.html', render_params

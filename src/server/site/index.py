from server.helpers import templateWrapper


@templateWrapper
def index():  # type: ignore
    return 'index.html', {}  # type: ignore

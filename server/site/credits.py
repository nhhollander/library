from server.helpers import exceptionWrapper, templateWrapper
from pathlib import Path
import json


@exceptionWrapper
@templateWrapper
def credits():
    """
    Generate a credits page from the credits file.

    TODO: Read the license field from the third party resources and add additional information to
    the output based on the license specifics, such as OSI/FSF approval and link to more info.
    """

    file_path = Path(__file__).parent.absolute()
    credits_file = Path(file_path, '../../credits.json')
    c = json.load(credits_file.open("r"))

    return 'credits.html', {"credits": c}

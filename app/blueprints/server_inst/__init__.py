__author__ = "Nigshoxiz"

from app.utils import get_version
# import libs
from flask import Blueprint
import logging

server_inst_page = Blueprint("server_inst_page", __name__,
                             template_folder='templates',
                             url_prefix='/server_inst')

logger = logging.getLogger("ob_panel")

version = get_version()
# import routes
from . import views
from . import dashboard
from . import console
from . import ftp
from . import create_inst
from . import edit_inst

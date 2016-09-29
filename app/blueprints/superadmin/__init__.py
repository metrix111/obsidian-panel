__author__ = "Nigshoxiz"

# import libs
from flask import Blueprint
# logging
import logging
super_admin_page = Blueprint("super_admin_page", __name__,
                             template_folder="templates",
                             url_prefix="/super_admin")

logger = logging.getLogger("ob_panel")
# import routes
from . import login
from . import server_core
from . import java_binary
from . import file_backup
from . import info
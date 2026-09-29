"""Apache mod_wsgi entry point."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import db  # noqa: E402
from app import app as application  # noqa: E402

db.init_db()

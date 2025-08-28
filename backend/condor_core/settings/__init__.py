#backend/condor_core/settings/__init__.py

import os

ENV = os.environ.get("DJANGO_ENV", "dev")  # default: dev

if ENV == "prod":
    from .prod import *
else:
    from .dev import *

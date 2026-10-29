import os

# The test database is SQLite; set a placeholder before importing production
# settings, which correctly require a database password outside DEBUG mode.
os.environ.setdefault("DB_PASSWORD", "test-only-unused")

from .settings import *


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/minute",
        "user": "10000/minute",
        "login": "10000/minute",
        "password_reset": "10000/minute",
    },
}

from .base import *  # noqa: F401, F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "fei_erp"),
        "USER": os.environ.get("POSTGRES_USER", "fei_erp"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "fei_erp_dev"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

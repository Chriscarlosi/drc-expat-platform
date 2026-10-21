from .settings import *
import dj_database_url

# ─────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────
# NEVER keep DEBUG=True in production
DEBUG = False

# Allow all hosts for now (we can restrict this to your domain later)
ALLOWED_HOSTS = ['drc-expat-platform.onrender.com', '127.0.0.1', 'localhost']

# ─────────────────────────────────────────────────────────────
# DATABASE (PostgreSQL via Docker)
# ─────────────────────────────────────────────────────────────
# Uses the DATABASE_URL environment variable injected by Docker
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3')
    )
}

# ─────────────────────────────────────────────────────────────
# STATIC FILES (WhiteNoise)
# ─────────────────────────────────────────────────────────────
# WhiteNoise allows Django to serve its own static files in production
# without needing a separate Nginx server.
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─────────────────────────────────────────────────────────────
# CELERY / REDIS
# ─────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config('REDIS_URL', default='redis://redis:6379/0')
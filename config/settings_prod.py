import os
from .settings import *
import dj_database_url

# ─────────────────────────────────────────────────────────────
# SECURITY & HOSTS
# ─────────────────────────────────────────────────────────────
DEBUG = False

# Dynamically add the Render URL to ALLOWED_HOSTS
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)

# Required for HTTPS forms on Render
CSRF_TRUSTED_ORIGINS = []
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")

# ─────────────────────────────────────────────────────────────
# DATABASE (PostgreSQL via Docker)
# ─────────────────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3')
    )
}

# ─────────────────────────────────────────────────────────────
# STATIC FILES (WhiteNoise)
# ─────────────────────────────────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─────────────────────────────────────────────────────────────
# CELERY / REDIS
# ─────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config('REDIS_URL', default='redis://redis:6379/0')
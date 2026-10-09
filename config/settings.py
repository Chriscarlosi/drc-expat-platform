"""
Django settings for the DRC Expat Expert & Visa Compliance Management Platform.
"""

from pathlib import Path
from decouple import config, Csv

# -------------------------------------------------------------------
# BASE
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='127.0.0.1,localhost')

# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
'django_otp',
'django_otp.plugins.otp_totp',
'django_otp.plugins.otp_static',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'modeltranslation',
    'encrypted_model_fields',
    'auditlog',

    # Local apps
    'apps.organization',
    'apps.experts',
    'apps.visas',
    'apps.compliance',
    'apps.documents',
    'apps.notifications',
    'apps.audit.apps.AuditConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'apps.organization.middleware.TenantContextMiddleware',   # ← ADD THIS
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# -------------------------------------------------------------------
# DATABASE — PostgreSQL
# -------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='127.0.0.1'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

# -------------------------------------------------------------------
# AUTH
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------------------------------------------------
# INTERNATIONALIZATION — English + French
# -------------------------------------------------------------------
LANGUAGE_CODE = config('DEFAULT_LANGUAGE', default='en')
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# -------------------------------------------------------------------
# STATIC / MEDIA
# -------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------
# DRF — REST API
# -------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# -------------------------------------------------------------------
# CORS — for WebStorm frontend later
# -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

# ─────────────────────────────────────────────────────────────
# EMAIL — Development (prints to terminal)
# For production: swap to SMTP backend
# ─────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@drc-expat-platform.cd'

# -------------------------------------------------------------------
# ENCRYPTED FILE FIELDS — AES-256
# -------------------------------------------------------------------
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

# -------------------------------------------------------------------
# CELERY — notification engine (T-90 / T-60 / T-30)
# -------------------------------------------------------------------
CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# -------------------------------------------------------------------
# ─── AUDIT LOG ────────────────────────────────────────────────
# Track only the business models explicitly registered in
# apps/audit/apps.py. Do NOT set to True — it causes infinite
# recursion because django-auditlog would also watch our own
# ImmutableAuditLog table.
AUDITLOG_INCLUDE_ALL_MODELS = False

# Track IP addresses on every entry (for security review)
AUDITLOG_DISABLE_REMOTE_ADDR = False

# Capture full JSON diff (SOC 2 requirement — "what changed")
AUDITLOG_STORE_JSON_FIELDS = True

# Mask sensitive fields so they never leak into the log
AUDITLOG_MASK_FIELDS = [
    "passport_number",
    "yellow_fever_card_number",
    "permit_number",
    "visa_number",
    "prolongation_number",
]

# ─── MFA ENFORCEMENT ──────────────────────────────────────────
# Set to False temporarily if you get locked out during dev
MFA_ENFORCED = True
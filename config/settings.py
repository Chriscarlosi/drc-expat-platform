"""
Django settings for the DRC Expat Expert & Visa Compliance Management Platform.
"""

from pathlib import Path
from decouple import config, Csv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


# -------------------------------------------------------------------
# BASE
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='build-fallback-key-do-not-use-in-prod')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='127.0.0.1,localhost')


# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------
INSTALLED_APPS = [
    # ─── Unfold (MUST be first) ───
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",

    # ─── Django built-in ───
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # ─── Third-party ───
    'rosetta',
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'modeltranslation',
    'encrypted_model_fields',
    'auditlog',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',

    # ─── Local apps ───
    'apps.organization',
    'apps.experts',
    'apps.visas',
    'apps.compliance',
    'apps.documents',
    'apps.notifications',
    'apps.travel',
    'apps.frontend',
    'apps.audit.apps.AuditConfig',
]


# -------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',        # ← must be here for i18n
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'apps.organization.middleware.TenantContextMiddleware',
    'apps.organization.middleware.MFAEnforcementMiddleware',
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
                'apps.frontend.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


import dj_database_url

# ─────────────────────────────────────────────────────────────
# DATABASE — Supports Render's DATABASE_URL and Local Postgres
# ─────────────────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3')
    )
}

# If DATABASE_URL is not set locally, fall back to your local .env variables
if not config('DATABASE_URL', default=None):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='drc_expat_db'),
        'USER': config('POSTGRES_USER', default='drc_admin'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='drc_secure_password_change_me'),
        'HOST': config('POSTGRES_HOST', default='127.0.0.1'),
        'PORT': config('POSTGRES_PORT', default='5432'),
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

# ─── Authentication Redirects ──────────────────────────
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

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

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'daily-visa-expiry-check': {
        'task': 'apps.visas.tasks.daily_visa_expiry_check',
        'schedule': crontab(hour=0, minute=0),  # Run at midnight Africa/Kinshasa
        'options': {
            'expires': 3600, # Task expires after 1 hour if not picked up
        }
    },
}


# -------------------------------------------------------------------
# AUDIT LOG
# -------------------------------------------------------------------
AUDITLOG_INCLUDE_ALL_MODELS = False
AUDITLOG_DISABLE_REMOTE_ADDR = False
AUDITLOG_STORE_JSON_FIELDS = True
AUDITLOG_MASK_FIELDS = [
    "passport_number",
    "yellow_fever_card_number",
    "permit_number",
    "visa_number",
    "prolongation_number",
]


# -------------------------------------------------------------------
# MFA ENFORCEMENT
# -------------------------------------------------------------------
MFA_ENFORCED = False


# -------------------------------------------------------------------
# BUSINESS RULES (Premium Configuration)
# -------------------------------------------------------------------
VISA_PROLONGATION_NOTICE_DAYS = 30  # Ticket A.2: Configurable 30-day rule
VISA_PROLONGATION_NOTICE_VERIFIED = False  # Mark as unverified until DGM confirms


# ═══════════════════════════════════════════════════════════════
# DJANGO UNFOLD — Enterprise Admin Theme
# ═══════════════════════════════════════════════════════════════

UNFOLD = {
    "SITE_TITLE": "DRC Expat Compliance Platform",
    "SITE_HEADER": "DRC Expat Compliance Platform",
    "SITE_SUBHEADER": "DGM & Ministry of Labour Management",
    "SITE_URL": "/",
    "SITE_SYMBOL": "verified_user",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "12px",
    "COLORS": {
        "primary": {
            "50":  "240 253 250",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 234 212",
            "400": "45 212 191",
            "500": "20 184 166", # Teal / Brand
            "600": "13 148 136",
            "700": "15 118 110",
            "800": "17 94 89",
            "900": "19 78 74",
            "950": "4 47 46",
        },
        "font": {
            "subtle-light": "100 116 139",
            "subtle-dark": "148 163 184",
            "default-light": "15 23 42",
            "default-dark": "248 250 252",
            "important-light": "2 6 23",
            "important-dark": "241 245 249",
        },
},
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Dashboard"),
                "separator": False,
                "items": [
                    {
                        "title": _("Risk Dashboard"),
                        "icon": "shield",
                        "link": reverse_lazy("compliance:dashboard"),
                    },
                ],
            },
            {
                "title": _("Compliance"),
                "separator": True,
                "items": [
                    {"title": _("Penalty Ledger"), "icon": "gavel",
                     "link": reverse_lazy("admin:compliance_penaltyledger_changelist")},
                    {"title": _("Cost Categories"), "icon": "category",
                     "link": reverse_lazy("admin:compliance_costcategory_changelist")},
                    {"title": _("Expert Costs"), "icon": "payments",
                     "link": reverse_lazy("admin:compliance_expertcost_changelist")},
                    {"title": _("Monthly Invoices"), "icon": "receipt_long",
                     "link": reverse_lazy("admin:compliance_monthlyinvoice_changelist")},
                ],
            },
            {
                "title": _("Experts"),
                "separator": True,
                "items": [
                    {"title": _("Expert Profiles"), "icon": "badge",
                     "link": reverse_lazy("admin:experts_expertprofile_changelist")},
                ],
            },
            {
                "title": _("Visas & Permits"),
                "separator": True,
                "items": [
                    {"title": _("Visa Records"), "icon": "flight_takeoff",
                     "link": reverse_lazy("admin:visas_visarecord_changelist")},
                    {"title": _("Visa Type Catalog"), "icon": "menu_book",
                     "link": reverse_lazy("admin:visas_visatypecatalog_changelist")},
                    {"title": _("Prolongations"), "icon": "schedule",
                     "link": reverse_lazy("admin:visas_visaprolongation_changelist")},
                    {"title": _("Cartes de Travail"), "icon": "work",
                     "link": reverse_lazy("admin:visas_cartedetravail_changelist")},
                ],
            },
            {
                "title": _("Organization"),
                "separator": True,
                "items": [
                    {"title": _("Companies"), "icon": "domain",
                     "link": reverse_lazy("admin:organization_company_changelist")},
                    {"title": _("Sites"), "icon": "location_on",
                     "link": reverse_lazy("admin:organization_site_changelist")},
                    {"title": _("Departments"), "icon": "account_tree",
                     "link": reverse_lazy("admin:organization_department_changelist")},
                ],
            },
            {
                "title": _("Security & Audit"),
                "separator": True,
                "items": [
                    {"title": _("Immutable Audit Log"), "icon": "security",
                     "link": reverse_lazy("admin:audit_immutableauditlog_changelist")},
                    {"title": _("Document Versions"), "icon": "folder_copy",
                     "link": reverse_lazy("admin:documents_documentversion_changelist")},
                    {"title": _("Users"), "icon": "group",
                     "link": reverse_lazy("admin:auth_user_changelist")},
                    {"title": _("Groups"), "icon": "shield_person",
                     "link": reverse_lazy("admin:auth_group_changelist")},
                ],
            },
            {
                "title": _("Travel & Charter"),
                "separator": True,
                "items": [
                    {"title": _("Flight Manifest Board"), "icon": "flight",
                     "link": reverse_lazy("admin:travel_charterflight_changelist")},
                    {"title": _("Rotation Calendar"), "icon": "calendar_month",
                     "link": reverse_lazy("travel:rotation_calendar")},
                    {"title": _("Medevac Readiness"), "icon": "emergency",
                     "link": reverse_lazy("travel:medevac_dashboard")},
                    {"title": _("Cost Dashboard"), "icon": "paid",
                     "link": reverse_lazy("travel:cost_dashboard")},
                    {"title": _("Charter Operators"), "icon": "flight_takeoff",
                     "link": reverse_lazy("admin:travel_charteroperator_changelist")},
                    {"title": _("Aircraft Fleet"), "icon": "airlines",
                     "link": reverse_lazy("admin:travel_aircraft_changelist")},
                    {"title": _("Routes"), "icon": "route",
                     "link": reverse_lazy("admin:travel_charterroute_changelist")},
                    {"title": _("Dependants"), "icon": "family_restroom",
                     "link": reverse_lazy("admin:travel_dependant_changelist")},
                    {"title": _("Travel Authorizations"), "icon": "fact_check",
                     "link": reverse_lazy("admin:travel_travelauthorization_changelist")},
                ],
            },
            {
                "title": _("Automation"),
                "separator": True,
                "items": [
                    {"title": _("Scheduled Tasks"), "icon": "schedule",
                     "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist")},
                    {"title": _("Task Results"), "icon": "check_circle",
                     "link": reverse_lazy("admin:django_celery_results_taskresult_changelist")},
                ],
            },
        ],
    },
}


# -------------------------------------------------------------------
# REGULATORY CONFIGURATION (Unverified - Pending Gazette)
# -------------------------------------------------------------------
DRC_EXPAT_QUOTA_CAP = 6.5  # Unverified
DRC_CATEGORY_CAPS = {  # Unverified
    "CLASS_I_V": 2.0,
    "SUPERVISOR": 2.5,
    "MANAGEMENT": 2.0,
}
DRC_REGULATORY_VERIFIED = False  # Set to True once confirmed by user

# ═══════════════════════════════════════════════════════════════
# AWS S3 STORAGE CONFIGURATION (Sprint 1)
# ═══════════════════════════════════════════════════════════════
import os
from decouple import config

# ═══════════════════════════════════════════════════════════════
# AWS S3 STORAGE CONFIGURATION (Sprint 1)
# ═══════════════════════════════════════════════════════════════
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = 'af-south-1' # Cape Town
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 900
AWS_DEFAULT_ACL = 'private'

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'
"""Django settings, read entirely from environment variables.

There is one settings module, not separate local and production ones: the app has a
single production and no staging, so the environment alone switches behaviour
(e.g. `DEBUG=false ... check --deploy` checks the production configuration).
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name):
    """A comma-separated environment variable as a list, ignoring blanks."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def parse_database_url(url):
    """Turn a `postgres://user:password@host:port/name` URL into Django's DATABASES entry.

    Done with the standard library (urllib) so no extra package is needed.
    Fails loudly: a silently wrong database is worse than a crash at startup.
    """
    parsed = urlparse(url or "")
    if parsed.scheme not in ("postgres", "postgresql") or not parsed.path.strip("/"):
        raise ValueError(
            "DATABASE_URL must look like postgres://user:password@host:port/name"
        )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
    }


SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.environ.get("DEBUG", "").lower() == "true"
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    # Unfold must come before django.contrib.admin so its templates override the admin's.
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rulebook",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files (the admin's CSS) straight from gunicorn.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# The scheduler's own Postgres, never availability's.
DATABASES = {"default": parse_database_url(os.environ.get("DATABASE_URL", ""))}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Dates are America/New_York calendar dates (CLAUDE.md conventions).
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Railway's health check calls over plain HTTP; a redirect would make it fail.
# Matched against the path without its leading slash. Always set, so a test can prove it.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]

if not DEBUG:
    # Production runs behind Railway's HTTPS proxy, which says so in this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600  # raise once the site is known to work over HTTPS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

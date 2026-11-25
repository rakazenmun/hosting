import os
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO = os.getenv("WNBASE_DEMO") == "1"
PUBLISH_ORIGIN = os.getenv("PUBLISH_ORIGIN", "http://127.0.0.1:8000" if DEMO else "https://sites.wnbase.com")
CONTENT_ORIGIN = os.getenv("CONTENT_ORIGIN", os.getenv("RENDER_EXTERNAL_URL", PUBLISH_ORIGIN))
APP_ORIGIN = os.getenv("APP_ORIGIN", "http://localhost:8000" if DEMO else PUBLISH_ORIGIN)
PUBLISH_ORIGIN = PUBLISH_ORIGIN.rstrip("/")
CONTENT_ORIGIN = CONTENT_ORIGIN.rstrip("/")
APP_ORIGIN = APP_ORIGIN.rstrip("/")
APP_HOST = urlsplit(APP_ORIGIN).hostname
PUBLISH_HOST = urlsplit(PUBLISH_ORIGIN).hostname
CONTENT_HOST = urlsplit(CONTENT_ORIGIN).hostname
if not APP_HOST or not PUBLISH_HOST or not CONTENT_HOST or APP_HOST == CONTENT_HOST:
    raise ImproperlyConfigured("Set a content origin on a different host from the dashboard.")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "").rstrip("/")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
ADMIN_CLERK_USERNAME = os.getenv("ADMIN_CLERK_USERNAME", "").strip()
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "wnbase-local-demo-only" if DEMO else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY or enable the local demo.")
DEBUG = DEMO
ALLOWED_HOSTS = list({APP_HOST, PUBLISH_HOST, CONTENT_HOST})
if render_host := os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(render_host)
CSRF_TRUSTED_ORIGINS = [APP_ORIGIN]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not DEMO
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
if not DEMO:
    SESSION_COOKIE_NAME = "__Host-wnbase-session"
    CSRF_COOKIE_NAME = "__Host-wnbase-csrf"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "hosting",
]
MIDDLEWARE = [
    "hosting.middleware.HostRouting",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "hosting.middleware.ClerkAuthentication",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if DEMO:
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
LOGIN_URL = "sign-in"
LOGIN_REDIRECT_URL = "workspace"
WNBASE_SITE_LIMIT_MIB = int(os.getenv("WNBASE_SITE_LIMIT_MIB", "25"))
WNBASE_SITE_FILE_LIMIT = int(os.getenv("WNBASE_SITE_FILE_LIMIT", "500"))
if not 1 <= WNBASE_SITE_LIMIT_MIB <= 50 or not 1 <= WNBASE_SITE_FILE_LIMIT <= 2000:
    raise ImproperlyConfigured("Set upload limits within 1–50 MiB and 1–2000 files.")

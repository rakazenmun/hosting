from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.functional import SimpleLazyObject


class HostRouting:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = urlsplit(f"//{request.get_host()}").hostname
        if host == settings.CONTENT_HOST:
            request.urlconf = "config.published_urls"
        elif host != settings.APP_HOST and request.path != "/healthz/":
            return HttpResponseRedirect(settings.APP_ORIGIN + "/")
        return self.get_response(request)


@lru_cache(maxsize=1)
def clerk_keys(issuer):
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", timeout=3)


def clerk_user(request, fallback):
    token = request.COOKIES.get("__session")
    if not token:
        return fallback
    issuer = settings.CLERK_ISSUER
    try:
        key = clerk_keys(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, key.key, algorithms=["RS256"], issuer=issuer, leeway=5,
            options={"require": ["sub", "iss", "exp", "nbf", "azp", "sid"]},
        )
    except jwt.PyJWTError:
        return fallback
    subject = claims["sub"]
    if claims["azp"] != settings.APP_ORIGIN or claims.get("sts", "active") != "active":
        return fallback
    if not subject.startswith("user_") or len(subject) > 80:
        return fallback
    with transaction.atomic():
        user, _ = get_user_model().objects.get_or_create(username=f"clerk:{subject}")
    if not user.is_active:
        return fallback
    request.clerk_subject = subject
    request.clerk_username = claims.get("wnbase_username")
    return user


class ClerkAuthentication:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.CLERK_ISSUER and not getattr(request, "urlconf", None):
            django_user = request.user
            request.user = SimpleLazyObject(lambda: clerk_user(request, django_user))
        return self.get_response(request)

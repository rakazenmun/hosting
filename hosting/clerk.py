import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)


class ClerkProfileError(Exception):
    pass


def clerk_profile_username(subject):
    request = Request(
        f"https://api.clerk.com/v1/users/{quote(subject, safe='')}",
        headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            profile = json.load(response)
    except HTTPError as exc:
        logger.warning("Clerk profile lookup rejected with HTTP %s", exc.code)
        raise ClerkProfileError from exc
    except (URLError, OSError, ValueError) as exc:
        logger.warning("Clerk profile lookup failed (%s)", type(exc).__name__)
        raise ClerkProfileError from exc
    if not isinstance(profile, dict) or profile.get("id") != subject:
        logger.warning("Clerk profile lookup returned an unexpected profile")
        raise ClerkProfileError
    return profile.get("username")

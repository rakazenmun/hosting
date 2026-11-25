import json
import logging
import re
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
        with exc:
            kind = exc.headers.get_content_type()
            code = None
            if kind == "application/json":
                try:
                    errors = json.loads(exc.read(4096)).get("errors", [])
                    candidate = errors[0].get("code")
                    if isinstance(candidate, str) and re.fullmatch(r"[a-z_]{1,64}", candidate):
                        code = candidate
                except (ValueError, AttributeError, IndexError, KeyError, TypeError, OSError):
                    pass
        logger.warning("Clerk profile lookup rejected with HTTP %s (%s)", exc.code, code or kind)
        raise ClerkProfileError from exc
    except (URLError, OSError, ValueError) as exc:
        logger.warning("Clerk profile lookup failed (%s)", type(exc).__name__)
        raise ClerkProfileError from exc
    if not isinstance(profile, dict) or profile.get("id") != subject:
        logger.warning("Clerk profile lookup returned an unexpected profile")
        raise ClerkProfileError
    return profile.get("username")

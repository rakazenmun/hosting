import json
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


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
    except (URLError, OSError, ValueError) as exc:
        raise ClerkProfileError from exc
    if not isinstance(profile, dict) or profile.get("id") != subject:
        raise ClerkProfileError
    return profile.get("username")

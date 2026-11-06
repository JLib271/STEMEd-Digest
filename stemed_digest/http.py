"""Small HTTPS helpers with retries (standard library only)."""
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "STEMEd-Digest/1.0 (+https://github.com/JLib271/STEMEd-Digest)"


def user_agent() -> str:
    """Crossref asks API users for a contact address. Set CONTACT_EMAIL (a repository
    variable) to use its faster "polite" pool; without it, requests stay anonymous."""
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    return f"{USER_AGENT[:-1]}; mailto:{email})" if email else USER_AGENT


def get_json(url: str, params: dict = None, tries: int = 4, timeout: int = 60) -> dict:
    return json.loads(get_text(url, params, tries, timeout, accept="application/json"))


def get_text(url: str, params: dict = None, tries: int = 4, timeout: int = 60, accept: str = "*/*") -> str:
    if params:
        url = f"{url}?{urlencode(params, safe='[]:|!,')}"
    last = None
    for attempt in range(tries):
        try:
            req = Request(url, headers={"User-Agent": user_agent(), "Accept": accept})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            wait = int(exc.headers.get("Retry-After") or 0) or 2 ** attempt * 3
        except (URLError, TimeoutError) as exc:
            last = exc
            wait = 2 ** attempt * 3
        time.sleep(min(wait, 60))
    shown = re.sub(r"api_key=[^&]+", "api_key=***", url)
    raise RuntimeError(f"Giving up on {shown}: {last}")

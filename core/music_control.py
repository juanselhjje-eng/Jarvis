from __future__ import annotations

"""Music intent adapter.

This module does not download or copy protected media. It opens an authorized
music service and searches for the requested track so the service itself
handles playback and account permissions.
"""

import re
import urllib.parse
import webbrowser


_SERVICE_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "youtube music": "https://music.youtube.com/search?q={q}",
    "spotify": "https://open.spotify.com/search/{q}",
}


def parse_track_request(text: str) -> tuple[str, str | None] | None:
    m = re.search(r"\breproduce\s+(.+)$", text.strip(), re.I)
    if not m:
        return None
    query = m.group(1).strip()
    if not query:
        return None
    service = None
    for name in _SERVICE_SEARCH:
        if name in query.lower():
            service = name
            query = re.sub(re.escape(name), "", query, flags=re.I).strip()
    query = re.sub(r"\bde\s+", " ", query, count=1, flags=re.I).strip()
    return query, service


def search_track(query: str, service: str | None = None) -> str:
    service = service or "youtube music"
    template = _SERVICE_SEARCH.get(service, _SERVICE_SEARCH["youtube music"])
    url = template.format(q=urllib.parse.quote_plus(query))
    webbrowser.open(url)
    return f"Buscando {query} en {service}."

"""Hermes plugin tools for secure Paperless-ngx metadata search and share-link creation."""

from __future__ import annotations

import ctypes
import datetime as dt
import json
from typing import Any
from urllib import error, parse, request


def _read_env(name: str) -> str:
    """Read an environment variable without importing os/pathlib."""
    getenv = ctypes.CDLL(None).getenv
    getenv.argtypes = [ctypes.c_char_p]
    getenv.restype = ctypes.c_char_p

    value = getenv(name.encode("utf-8"))
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    decoded = value.decode("utf-8").strip()
    if not decoded:
        raise RuntimeError(f"Environment variable is empty: {name}")

    return decoded


def _base_url() -> str:
    return _read_env("PAPERLESS_URL").rstrip("/")


def _auth_token() -> str:
    return _read_env("PAPERLESS_API_TOKEN")


def _paperless_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Issue an authenticated JSON request to Paperless-ngx."""
    url = f"{_base_url()}{path}"
    data = None
    headers = {
        "Authorization": f"Token {_auth_token()}",
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, method=method.upper(), data=data, headers=headers)

    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Paperless API error {exc.code} for {method.upper()} {path}: {detail}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach Paperless API at {url}: {exc.reason}") from exc

    if not body:
        return {}

    try:
        parsed: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Paperless API returned invalid JSON for {method.upper()} {path}") from exc

    return parsed


def _paperless_request_url(url: str) -> dict[str, Any]:
    """Issue an authenticated JSON GET request to a fully qualified Paperless URL."""
    headers = {
        "Authorization": f"Token {_auth_token()}",
        "Accept": "application/json",
    }
    req = request.Request(url=url, method="GET", headers=headers)

    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Paperless API error {exc.code} for GET {url}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach Paperless API at {url}: {exc.reason}") from exc

    if not body:
        return {}

    try:
        parsed: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Paperless API returned invalid JSON for GET {url}") from exc

    return parsed


def search_paperless(
    query: str,
    max_results: int = 25,
    correspondent_id: int | None = None,
    document_type_id: int | None = None,
    tag_ids: list[int] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    is_in_inbox: bool | None = None,
) -> dict[str, Any]:
    """Search documents and return a minimal metadata-only result set."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError("max_results must be a positive integer")

    max_results = min(max_results, 100)

    params_dict: dict[str, Any] = {"query": query.strip()}
    
    # Build parameter dict with only non-None values
    if correspondent_id is not None and isinstance(correspondent_id, int) and correspondent_id > 0:
        params_dict["correspondent"] = correspondent_id
    if document_type_id is not None and isinstance(document_type_id, int) and document_type_id > 0:
        params_dict["document_type"] = document_type_id
    if tag_ids is not None and isinstance(tag_ids, list):
        for tag_id in tag_ids:
            if isinstance(tag_id, int) and tag_id > 0:
                params_dict.setdefault("tag", []).append(tag_id)
    if created_after is not None and isinstance(created_after, str):
        params_dict["created__date__gte"] = created_after.strip()
    if created_before is not None and isinstance(created_before, str):
        params_dict["created__date__lte"] = created_before.strip()
    if is_in_inbox is not None and isinstance(is_in_inbox, bool):
        params_dict["is_in_inbox"] = str(is_in_inbox).lower()
    
    # Build query string, handling repeated parameters (e.g., multiple tags)
    query_parts = []
    for key, val in params_dict.items():
        if isinstance(val, list):
            for v in val:
                query_parts.append(f"{parse.quote_plus(key)}={parse.quote_plus(str(v))}")
        else:
            query_parts.append(f"{parse.quote_plus(key)}={parse.quote_plus(str(val))}")
    params = "&".join(query_parts) if query_parts else ""
    
    first_page = _paperless_request("GET", f"/api/documents/?{params}")

    total_available = first_page.get("count")
    if not isinstance(total_available, int) or total_available < 0:
        total_available = 0

    raw_results = first_page.get("results", [])
    if not isinstance(raw_results, list):
        raise RuntimeError("Unexpected Paperless response: results is not a list")

    filtered_results: list[dict[str, Any]] = []

    def _append_items(items: list[Any]) -> None:
        for item in items:
            if len(filtered_results) >= max_results:
                return
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            title = item.get("title")
            created = item.get("created")
            if not isinstance(item_id, int) or not isinstance(title, str) or not isinstance(created, str):
                continue
            filtered_results.append(
                {
                    "id": item_id,
                    "title": title,
                    "created": created,
                }
            )

    _append_items(raw_results)

    next_url = first_page.get("next")
    while isinstance(next_url, str) and next_url and len(filtered_results) < max_results:
        page_data = _paperless_request_url(next_url)
        next_results = page_data.get("results", [])
        if not isinstance(next_results, list):
            raise RuntimeError("Unexpected Paperless response: results is not a list")
        _append_items(next_results)
        next_url = page_data.get("next")

    return {
        "total_available": total_available,
        "count": len(filtered_results),
        "results": filtered_results,
    }


def create_share_link(document_id: int, expiration_days: int | None = 1) -> dict[str, Any]:
    """Create a Paperless share link for archive file version only."""
    if not isinstance(document_id, int) or document_id < 1:
        raise ValueError("document_id must be a positive integer")

    expiration_value: str | None = None
    if expiration_days is not None:
        if not isinstance(expiration_days, int) or expiration_days < 1:
            raise ValueError("expiration_days must be a positive integer when provided")
        expiration_date = dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=expiration_days)
        expiration_value = expiration_date.isoformat()

    payload: dict[str, Any] = {
        "document": document_id,
        "file_version": "archive",
    }
    if expiration_value is not None:
        payload["expiration"] = expiration_value

    data = _paperless_request("POST", "/api/share_links/", payload)

    share_link = data.get("share_link") or data.get("url") or data.get("link")
    if not isinstance(share_link, str) or not share_link.strip():
        slug = data.get("slug")
        if isinstance(slug, str) and slug.strip():
            share_link = f"{_base_url()}/share/{slug.strip()}"
        else:
            raise RuntimeError("Paperless API response did not include a share link URL")

    return {
        "document_id": document_id,
        "share_link": share_link.strip(),
        "expiration": expiration_value,
    }

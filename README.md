# Hermes Paperless Share Plugin

Hermes Agent plugin for Paperless-ngx focused on metadata search and share-link generation.

This plugin provides two tools:

- `search_paperless`: metadata search only
- `create_share_link`: create Paperless share links for archive file version

## Security Model

- This plugin does not expose any document-download tool.
- This plugin performs no disk I/O in runtime tool logic.
- No `os` or `pathlib` imports in `main.py`.
- Uses API token auth against Paperless-ngx.
- Search responses are filtered with only fields limited to  `id`, `title`, and `created` to reduce LLM context size.
- Search is paginated and capped to a configurable maximum result count.
- Note: effective download prevention depends on runtime controls and token scope outside this plugin.

## Files

- `plugin.yaml`: plugin manifest and tool registration
- `schemas.py`: JSON schemas for tool inputs/outputs
- `main.py`: tool implementation

## Required Environment Variables

Set these in the runtime environment where Hermes executes the plugin:

- `PAPERLESS_URL` (example: `https://paperless.example.com`)
- `PAPERLESS_API_TOKEN` (Paperless-ngx API token)

## Tool Details

### 1) `search_paperless(query)`

Behavior:

- Calls `GET /api/documents/?query=<query>` and follows pagination until the configured result cap is reached
- Supports optional filters: `correspondent_id`, `document_type_id`, `tag_ids`, `created_after`, `created_before`, `is_in_inbox`
- Returns only these fields per document:
  - `id`
  - `title`
  - `created`
- Also returns:
  - `total_available` for the full match count reported by Paperless
  - `count` for the number of documents actually returned

Example input:

```json
{
  "query": "invoice acme april",
  "max_results": 10,
  "correspondent_id": 2,
  "tag_ids": [5, 7],
  "created_after": "2026-04-01"
}
```

Example output:

```json
{
  "total_available": 42,
  "count": 1,
  "results": [
    {
      "id": 183,
      "title": "ACME Invoice 2026-04",
      "created": "2026-04-13T10:12:52.345678Z"
    }
  ]
}
```

Parameters:

- `query` (required): Search query across all metadata
- `max_results` (optional, default 25): How many documents to return, capped at 100
- `correspondent_id` (optional): Filter by correspondent ID
- `document_type_id` (optional): Filter by document type ID
- `tag_ids` (optional): Array of tag IDs to filter by (documents matching any of these tags)
- `created_after` (optional): ISO date string (YYYY-MM-DD); filter to documents created on or after this date
- `created_before` (optional): ISO date string (YYYY-MM-DD); filter to documents created on or before this date
- `is_in_inbox` (optional): Boolean; filter to inbox documents (true) or non-inbox (false)

### 2) `create_share_link(document_id, expiration_days=1)`

Behavior:

- Calls `POST /api/share_links/`
- Always sends payload:

```json
{
  "document": 183,
  "file_version": "archive"
}
```

- If `expiration_days` is provided (or omitted, defaulting to 1), computes UTC date and sends:
  - `"expiration": "YYYY-MM-DD"`

Example input:

```json
{
  "document_id": 183,
  "expiration_days": 1
}
```

Example output:

```json
{
  "document_id": 183,
  "share_link": "https://paperless.example.com/share/abc123def456",
  "expiration": "2026-05-18"
}
```

## Notes

- This plugin is designed for handing share links to users or passing links as text to another plugin (for example, Google Workspace integration).
- It intentionally does not fetch file bytes and does not write local files.
- Use `max_results` when you want a smaller or larger search slice from a broader Paperless corpus.

- I did not go with existing plugins as I really don't need much of the functionality they provide, and I wanted to keep this focused on metadata search and share link generation. Even the search tool is focused on metadata only, to minimise context size.
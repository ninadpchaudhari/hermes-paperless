"""Tool schemas for the Hermes Paperless-ngx plugin."""

SEARCH_PAPERLESS_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "minLength": 1,
            "description": "Search query for document metadata.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 25,
            "description": "Maximum number of filtered documents to return.",
            },
            "correspondent_id": {
                "type": ["integer", "null"],
                "minimum": 1,
                "description": "Filter to a specific correspondent ID.",
            },
            "document_type_id": {
                "type": ["integer", "null"],
                "minimum": 1,
                "description": "Filter to a specific document type ID.",
            },
            "tag_ids": {
                "type": ["array", "null"],
                "items": {"type": "integer", "minimum": 1},
                "description": "Filter to documents with any of these tag IDs.",
            },
            "created_after": {
                "type": ["string", "null"],
                "description": "Filter to documents created on or after this ISO date (YYYY-MM-DD).",
            },
            "created_before": {
                "type": ["string", "null"],
                "description": "Filter to documents created on or before this ISO date (YYYY-MM-DD).",
            },
            "is_in_inbox": {
                "type": ["boolean", "null"],
                "description": "Filter to documents in inbox (true) or not in inbox (false).",
        }
    },
    "required": ["query"],
    "additionalProperties": False,
}

SEARCH_PAPERLESS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "total_available": {
            "type": "integer",
            "minimum": 0,
            "description": "Total documents matching the query across all pages.",
        },
        "count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of filtered documents returned.",
        },
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "created": {"type": "string"},
                },
                "required": ["id", "title", "created"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["total_available", "count", "results"],
    "additionalProperties": False,
}

CREATE_SHARE_LINK_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Paperless document id.",
        },
        "expiration_days": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "Optional number of days until link expiration.",
        },
    },
    "required": ["document_id"],
    "additionalProperties": False,
}

CREATE_SHARE_LINK_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {"type": "integer", "minimum": 1},
        "share_link": {
            "type": "string",
            "minLength": 1,
            "description": "Generated Paperless share URL.",
        },
        "expiration": {
            "type": ["string", "null"],
            "description": "Expiration date in YYYY-MM-DD if provided.",
        },
    },
    "required": ["document_id", "share_link", "expiration"],
    "additionalProperties": False,
}

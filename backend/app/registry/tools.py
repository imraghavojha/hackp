SEED_TOOL_REGISTRY = [
    {
        "id": "tool_lead_formatter_v1",
        "name": "Lead List Formatter",
        "description": "Formats portal lead CSVs into Bob's preferred output.",
        "trigger": {
            "type": "on_url_visit",
            "url_pattern": "portal.example.com/leads",
            "prompt": "I noticed you format lead exports every morning.",
        },
    }
]

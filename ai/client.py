from __future__ import annotations

from typing import Any


def detect_transformation(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events", [])
    if len(events) < 2:
        return {"detected": False}

    return {
        "detected": True,
        "signature": "sig_domain_a_lead_formatter",
        "confidence": 0.82,
        "transformation_name": "Lead List Formatter",
        "summary": "Formats lead exports into Bob's preferred spreadsheet output.",
        "input_characterization": "csv export from portal",
        "output_characterization": "xlsx with tags and sorted rows",
        "event_window": {"start": events[0]["timestamp"], "end": events[-1]["timestamp"]},
        "repetition_count": max(2, len(events)),
    }


def generate_tool(payload: dict[str, Any]) -> dict[str, Any]:
    detection = payload.get("detection", {})
    return {
        "name": detection.get("transformation_name", "Untitled Tool"),
        "description": "Generated from observed repeated work.",
        "transformation_summary": ["Parse input", "Apply worker-specific rules", "Return formatted output"],
        "html_artifact": "<!DOCTYPE html><html><body><script>window.Tool={metadata:{id:'tool_stub',name:'Tool',version:'0.1.0',input_type:'text',output_type:'text'},async transform(input){return input},defaultConfig:{}}</script></body></html>",
        "input_spec": {"primary_input": "csv_file", "accepts": ["paste", "file_drop", "file_picker"]},
        "output_spec": {"format": "xlsx", "filename_pattern": "leads_{YYYY-MM-DD}.xlsx"},
        "trigger": {
            "type": "on_url_visit",
            "url_pattern": "portal.example.com/leads",
            "prompt": "I built you a tool for this.",
        },
        "ui_prefs": {"theme": "dark", "density": "compact"},
        "primitives_used": ["papaparse", "sheetjs"],
        "programmatic_interface": {"input_type": "csv_string", "output_type": "xlsx_blob"},
    }

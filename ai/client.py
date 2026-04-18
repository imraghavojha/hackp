from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.contracts import DetectionRequest, DetectionResponse, GenerateToolRequest
from ai.mem0_wrapper.client import (
    build_preferences_block,
    infer_density,
    infer_initials,
    infer_tag_pattern,
    infer_theme,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
CDN_REGISTRY_PATH = ROOT_DIR / "runtime" / "cdn.json"
DETECTION_SIGNATURE = "sig_domain_a_lead_formatter"
LEADS_URL_PATTERN = "portal.example.com/leads"


def detect_transformation(payload: dict[str, Any]) -> dict[str, Any]:
    request = DetectionRequest.model_validate(payload)
    if DETECTION_SIGNATURE in request.existing_tool_signatures:
        return {"detected": False}

    critical_events = [event for event in request.events if event.event_type in {"copy", "paste", "input", "submit", "file_download"}]
    if len(critical_events) < 2:
        return {"detected": False}

    if not any(LEADS_URL_PATTERN in event.url for event in request.events):
        return {"detected": False}

    response = DetectionResponse(
        detected=True,
        signature=DETECTION_SIGNATURE,
        confidence=0.82,
        transformation_name="Lead List Formatter",
        summary="Formats repeated lead exports into the worker's preferred spreadsheet output.",
        input_characterization="CSV export from the leads portal",
        output_characterization="XLSX file with filtered rows and a generated tag column",
        event_window={"start": request.events[0].timestamp, "end": request.events[-1].timestamp},
        repetition_count=max(2, len(critical_events) // 2),
    )
    return response.model_dump(mode="json")


def generate_tool(payload: dict[str, Any]) -> dict[str, Any]:
    request = GenerateToolRequest.model_validate(payload)
    detection = request.detection
    preferences_block = build_preferences_block(request.user_id, request.user_prefs_hint)
    theme = infer_theme(preferences_block)
    density = infer_density(preferences_block)
    initials = infer_initials(request.user_id, preferences_block)
    tag_pattern = infer_tag_pattern(preferences_block)
    html_artifact = _render_domain_a_tool(
        name=detection.get("transformation_name", "Lead List Formatter"),
        description="Drop your lead CSV, preview the cleaned output, and download a CRM-ready spreadsheet.",
        theme=theme,
        density=density,
        initials=initials,
        tag_pattern=tag_pattern,
    )
    return {
        "name": detection.get("transformation_name", "Untitled Tool"),
        "description": "Generated from repeated lead-export work observed in the browser.",
        "transformation_summary": [
            "Parse portal CSV input",
            "Filter for Series B+ fintech leads",
            "Sort by employee count descending",
            "Add the worker's outbound tag pattern",
            "Export an XLSX workbook",
        ],
        "html_artifact": html_artifact,
        "input_spec": {"primary_input": "csv_file", "accepts": ["paste", "file_drop", "file_picker"]},
        "output_spec": {"format": "xlsx", "filename_pattern": "leads_{YYYY-MM-DD}.xlsx"},
        "trigger": {
            "type": "on_url_visit",
            "url_pattern": LEADS_URL_PATTERN,
            "prompt": "Ready to format today's leads?",
        },
        "ui_prefs": {
            "theme": theme,
            "density": density,
            "primary_label": "Format My Leads",
            "show_preview": True,
        },
        "primitives_used": ["papaparse", "sheetjs"],
        "programmatic_interface": {"input_type": "csv_string", "output_type": "xlsx_blob"},
    }


def _render_domain_a_tool(
    *,
    name: str,
    description: str,
    theme: str,
    density: str,
    initials: str,
    tag_pattern: str,
) -> str:
    cdn_registry = json.loads(CDN_REGISTRY_PATH.read_text(encoding="utf-8"))
    cdn_scripts = "\n".join(
        [
            f'<script src="{cdn_registry["papaparse"]}"></script>',
            f'<script src="{cdn_registry["sheetjs"]}"></script>',
        ]
    )
    metadata = {
        "id": "tool_lead_formatter_generated_v1",
        "name": name,
        "version": "1.0",
        "input_type": "csv_string",
        "output_type": "xlsx_blob",
    }
    default_config = {
        "industry": "Fintech",
        "filter_min_stage": "series_b",
        "initials": initials,
        "tag_pattern": tag_pattern,
        "sort_by": "employees_desc",
    }
    background = "#f8fafc" if theme == "light" else "#09111f"
    surface = "#ffffff" if theme == "light" else "#0f172a"
    foreground = "#0f172a" if theme == "light" else "#e2e8f0"
    accent = "#0f766e" if theme == "light" else "#38bdf8"
    padding = "20px" if density == "comfortable" else "14px"
    html_template = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>__TOOL_NAME__</title>
    <style>
      :root {
        color-scheme: __COLOR_SCHEME__;
        --bg: __BACKGROUND__;
        --surface: __SURFACE__;
        --fg: __FOREGROUND__;
        --muted: __MUTED__;
        --accent: __ACCENT__;
        --pad: __PADDING__;
      }
      body {
        margin: 0;
        background: radial-gradient(circle at top, rgba(56, 189, 248, 0.18), transparent 35%), var(--bg);
        color: var(--fg);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }
      main {
        max-width: 960px;
        margin: 0 auto;
        padding: 48px 20px 64px;
      }
      .shell {
        background: var(--surface);
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 20px;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.25);
        overflow: hidden;
      }
      header {
        padding: 28px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
      }
      h1 {
        margin: 0 0 8px;
        font-size: clamp(1.8rem, 3vw, 2.5rem);
      }
      p {
        margin: 0;
        color: var(--muted);
      }
      .body {
        display: grid;
        gap: 18px;
        padding: 28px;
      }
      textarea, pre {
        width: 100%;
        box-sizing: border-box;
        min-height: 200px;
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.24);
        background: rgba(15, 23, 42, 0.08);
        color: var(--fg);
        padding: var(--pad);
        font: inherit;
      }
      pre {
        overflow: auto;
        white-space: pre-wrap;
      }
      .actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }
      button {
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        font-weight: 600;
        cursor: pointer;
      }
      .primary {
        background: var(--accent);
        color: #04131d;
      }
      .secondary {
        background: transparent;
        color: var(--fg);
        border: 1px solid rgba(148, 163, 184, 0.28);
      }
      .status {
        color: var(--muted);
        font-size: 0.95rem;
      }
    </style>
  </head>
  <body>
    <main>
      <section class="shell">
        <header>
          <h1>__TOOL_NAME__</h1>
          <p>__TOOL_DESCRIPTION__</p>
        </header>
        <div class="body">
          <label for="input-area">Paste the raw leads CSV</label>
          <textarea id="input-area" spellcheck="false" placeholder="company,industry,stage,employees,domain"></textarea>
          <div class="actions">
            <button class="secondary" id="preview-button">Preview Output</button>
            <button class="primary" id="download-button">Format My Leads</button>
          </div>
          <div class="status" id="status">Paste CSV rows, then preview or download.</div>
          <pre id="preview">Preview will appear here.</pre>
        </div>
      </section>
    </main>
    __CDN_SCRIPTS__
    <script>
      const TOOL_METADATA = __TOOL_METADATA__;
      const TOOL_DEFAULT_CONFIG = __DEFAULT_CONFIG__;
      const STAGE_RANK = { seed: 0, series_a: 1, series_b: 2, series_c: 3, series_d: 4, ipo: 5 };

      function fallbackCsvParse(text) {
        return String(text || "")
          .trim()
          .split(/\\r?\\n/)
          .filter(Boolean)
          .map((line) => line.split(","));
      }

      function parseCsv(text) {
        if (window.Papa && text.trim()) {
          return window.Papa.parse(text.trim(), { skipEmptyLines: true }).data;
        }
        return fallbackCsvParse(text);
      }

      function stageValue(rawStage) {
        return STAGE_RANK[String(rawStage || "").trim().toLowerCase().replace(/\\s+/g, "_")] || 0;
      }

      function normalizeIndustry(rawIndustry) {
        return String(rawIndustry || "").trim().toLowerCase();
      }

      function buildPreviewRows(input, config) {
        const rows = parseCsv(String(input || ""));
        if (!rows.length) {
          return [];
        }

        const [header, ...body] = rows;
        const index = Object.fromEntries(header.map((name, position) => [String(name).trim().toLowerCase(), position]));
        const industryIndex = index["industry"];
        const stageIndex = index["stage"];
        const employeesIndex = index["employees"];
        const outputHeader = [...header, "tag"];

        const filtered = body
          .filter((row) => {
            const industry = normalizeIndustry(row[industryIndex]);
            const passesIndustry = industry.includes(String(config.industry || "fintech").toLowerCase());
            const passesStage = stageValue(row[stageIndex]) >= stageValue(config.filter_min_stage);
            return passesIndustry && passesStage;
          })
          .sort((left, right) => Number(right[employeesIndex] || 0) - Number(left[employeesIndex] || 0))
          .map((row) => {
            const industryToken = String(row[industryIndex] || config.industry || "Fintech").replace(/\\s+/g, "");
            const tag = String(config.tag_pattern || "[Q2-Outbound-{industry}-{initials}]")
              .replaceAll("{industry}", industryToken)
              .replaceAll("{initials}", String(config.initials || "BK").toUpperCase());
            return [...row, tag];
          });

        return [outputHeader, ...filtered];
      }

      async function transformLeadCsv(input, config = {}) {
        const merged = { ...TOOL_DEFAULT_CONFIG, ...config };
        const rows = buildPreviewRows(input, merged);
        if (!rows.length) {
          return new Blob([""], { type: "text/plain;charset=utf-8" });
        }

        if (window.XLSX) {
          const worksheet = window.XLSX.utils.aoa_to_sheet(rows);
          const workbook = window.XLSX.utils.book_new();
          window.XLSX.utils.book_append_sheet(workbook, worksheet, "Formatted Leads");
          const array = window.XLSX.write(workbook, { bookType: "xlsx", type: "array" });
          return new Blob([array], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          });
        }

        const csv = rows.map((row) => row.join(",")).join("\\n");
        return new Blob([csv], { type: "text/csv;charset=utf-8" });
      }

      window.Tool = {
        metadata: TOOL_METADATA,
        defaultConfig: TOOL_DEFAULT_CONFIG,
        async transform(input, config = {}) {
          return transformLeadCsv(input, config);
        },
        debugPreview(input, config = {}) {
          return buildPreviewRows(input, { ...TOOL_DEFAULT_CONFIG, ...config });
        }
      };

      const inputArea = document.getElementById("input-area");
      const previewElement = document.getElementById("preview");
      const statusElement = document.getElementById("status");

      function renderPreview() {
        const rows = window.Tool.debugPreview(inputArea.value);
        previewElement.textContent = rows.length
          ? rows.map((row) => row.join(" | ")).join("\\n")
          : "No matching rows yet. Paste a leads CSV with fintech companies and stages.";
        statusElement.textContent = rows.length
          ? `Preview ready: ${Math.max(rows.length - 1, 0)} lead rows matched your rules.`
          : "No matching rows yet.";
      }

      document.getElementById("preview-button").addEventListener("click", renderPreview);
      document.getElementById("download-button").addEventListener("click", async () => {
        renderPreview();
        const blob = await window.Tool.transform(inputArea.value);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "leads_formatted.xlsx";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        statusElement.textContent = "Download started.";
      });
    </script>
  </body>
</html>
"""
    return (
        html_template.replace("__TOOL_NAME__", name)
        .replace("__TOOL_DESCRIPTION__", description)
        .replace("__COLOR_SCHEME__", "light" if theme == "light" else "dark")
        .replace("__BACKGROUND__", background)
        .replace("__SURFACE__", surface)
        .replace("__FOREGROUND__", foreground)
        .replace("__MUTED__", "#475569" if theme == "light" else "#94a3b8")
        .replace("__ACCENT__", accent)
        .replace("__PADDING__", padding)
        .replace("__CDN_SCRIPTS__", cdn_scripts)
        .replace("__TOOL_METADATA__", json.dumps(metadata))
        .replace("__DEFAULT_CONFIG__", json.dumps(default_config))
    )

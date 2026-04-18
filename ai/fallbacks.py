from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
CDN_REGISTRY_PATH = ROOT_DIR / "runtime" / "cdn.json"

DomainKey = Literal["domain_a", "domain_b", "domain_c"]


DOMAIN_DEFINITIONS: dict[DomainKey, dict[str, Any]] = {
    "domain_a": {
        "signature": "sig_domain_a_lead_formatter",
        "name": "Lead List Formatter",
        "summary": "Formats repeated lead exports into the worker's preferred spreadsheet output.",
        "input_characterization": "CSV export from the leads portal",
        "output_characterization": "XLSX file with filtered rows and a generated tag column",
        "url_pattern": "portal.example.com/leads",
        "default_prompt": "Ready to format today's leads?",
        "primary_label": "Format My Leads",
        "input_spec": {"primary_input": "csv_file", "accepts": ["paste", "file_drop", "file_picker"]},
        "output_spec": {"format": "xlsx", "filename_pattern": "leads_{YYYY-MM-DD}.xlsx"},
        "primitives_used": ["papaparse", "sheetjs"],
        "programmatic_interface": {"input_type": "csv_string", "output_type": "xlsx_blob"},
        "default_config": {
            "industry": "Fintech",
            "filter_min_stage": "series_b",
            "initials": "BK",
            "tag_pattern": "[Q2-Outbound-{industry}-{initials}]",
            "sort_by": "employees_desc",
        },
        "transformation_summary": [
            "Parse portal CSV input",
            "Filter for Series B+ fintech leads",
            "Sort by employee count descending",
            "Add the worker's outbound tag pattern",
            "Export an XLSX workbook",
        ],
    },
    "domain_b": {
        "signature": "sig_domain_b_market_brief",
        "name": "Market Brief Builder",
        "summary": "Turns a repeated ticker review into a compact watchlist brief.",
        "input_characterization": "Ticker list plus market data JSON",
        "output_characterization": "Copy-ready HTML watchlist brief",
        "url_pattern": "research.example.com/tickers",
        "default_prompt": "Want a quick brief for these tickers?",
        "primary_label": "Build Brief",
        "input_spec": {"primary_input": "json", "accepts": ["paste"]},
        "output_spec": {"format": "html", "filename_pattern": "market_brief_{YYYY-MM-DD}.html"},
        "primitives_used": [],
        "programmatic_interface": {"input_type": "json", "output_type": "html"},
        "default_config": {
            "heading": "Morning Watchlist",
            "tone": "concise and analytical",
            "max_points": 3,
        },
        "transformation_summary": [
            "Parse a short ticker list and market data payload",
            "Summarize the watchlist in analyst-ready language",
            "Output a compact HTML brief",
        ],
    },
    "domain_c": {
        "signature": "sig_domain_c_reply_drafter",
        "name": "Support Reply Drafter",
        "summary": "Drafts a calm customer reply from a repeated ticket triage pattern.",
        "input_characterization": "Support ticket JSON and customer profile JSON",
        "output_characterization": "Copy-ready support reply text",
        "url_pattern": "support.example.com/tickets",
        "default_prompt": "I drafted a reply for this ticket.",
        "primary_label": "Draft Reply",
        "input_spec": {"primary_input": "json", "accepts": ["paste"]},
        "output_spec": {"format": "text", "filename_pattern": "reply_{YYYY-MM-DD}.txt"},
        "primitives_used": [],
        "programmatic_interface": {"input_type": "json", "output_type": "text"},
        "default_config": {
            "tone": "calm and direct",
            "signoff": "Best,\nKai",
        },
        "transformation_summary": [
            "Parse the ticket and customer context",
            "Draft a concise empathetic reply",
            "Output copy-ready support text",
        ],
    },
}


def classify_domain_from_events(events: list[Any]) -> DomainKey | None:
    urls = " ".join(
        str(event.get("url", "")) if isinstance(event, dict) else str(getattr(event, "url", ""))
        for event in events
    )
    if DOMAIN_DEFINITIONS["domain_a"]["url_pattern"] in urls:
        return "domain_a"
    if DOMAIN_DEFINITIONS["domain_b"]["url_pattern"] in urls:
        return "domain_b"
    if DOMAIN_DEFINITIONS["domain_c"]["url_pattern"] in urls:
        return "domain_c"
    return None


def infer_repetition_count(events: list[dict[str, Any]]) -> int:
    output_events = [event for event in events if event.get("event_type") in {"submit", "file_download"}]
    if output_events:
      return len(output_events)
    critical_events = [event for event in events if event.get("event_type") in {"copy", "paste", "input", "submit", "file_download"}]
    return max(2, len(critical_events) // 2)


def domain_from_signature(signature: str | None) -> DomainKey | None:
    if signature is None:
        return None
    for key, definition in DOMAIN_DEFINITIONS.items():
        if definition["signature"] == signature:
            return key
    return None


def build_detection_response(domain: DomainKey, events: list[dict[str, Any]], confidence: float, summary: str | None = None) -> dict[str, Any]:
    definition = DOMAIN_DEFINITIONS[domain]
    return {
        "detected": True,
        "signature": definition["signature"],
        "confidence": confidence,
        "transformation_name": definition["name"],
        "summary": summary or definition["summary"],
        "input_characterization": definition["input_characterization"],
        "output_characterization": definition["output_characterization"],
        "event_window": {
            "start": events[0]["timestamp"],
            "end": events[-1]["timestamp"],
        },
        "repetition_count": infer_repetition_count(events),
    }


def corporate_palette(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "color_scheme": "dark",
            "background": "#111827",
            "surface": "#1f2937",
            "foreground": "#f3f4f6",
            "muted": "#9ca3af",
            "accent": "#1d4ed8",
            "accent_soft": "rgba(29, 78, 216, 0.12)",
            "border": "rgba(148, 163, 184, 0.24)",
        }
    return {
        "color_scheme": "light",
        "background": "#f3f4f6",
        "surface": "#ffffff",
        "foreground": "#111827",
        "muted": "#6b7280",
        "accent": "#1d4ed8",
        "accent_soft": "rgba(29, 78, 216, 0.08)",
        "border": "rgba(148, 163, 184, 0.28)",
    }


def build_generate_response(
    *,
    domain: DomainKey,
    name: str,
    description: str,
    transformation_summary: list[str],
    trigger_prompt: str,
    ui_prefs: dict[str, Any],
    default_config: dict[str, Any],
) -> dict[str, Any]:
    definition = DOMAIN_DEFINITIONS[domain]
    html_artifact = render_domain_tool(
        domain=domain,
        name=name,
        description=description,
        theme=ui_prefs.get("theme", "light"),
        density=ui_prefs.get("density", "comfortable"),
        default_config=default_config,
    )
    return {
        "name": name,
        "description": description,
        "transformation_summary": transformation_summary,
        "html_artifact": html_artifact,
        "input_spec": definition["input_spec"],
        "output_spec": definition["output_spec"],
        "trigger": {
            "type": "on_url_visit",
            "url_pattern": definition["url_pattern"],
            "prompt": trigger_prompt,
        },
        "ui_prefs": {
            "theme": ui_prefs.get("theme", "light"),
            "density": ui_prefs.get("density", "comfortable"),
            "primary_label": ui_prefs.get("primary_label", definition["primary_label"]),
            "show_preview": True,
        },
        "primitives_used": definition["primitives_used"],
        "programmatic_interface": definition["programmatic_interface"],
    }


def heuristic_generate_response(domain: DomainKey, *, theme: str, density: str, initials: str, tag_pattern: str) -> dict[str, Any]:
    definition = DOMAIN_DEFINITIONS[domain]
    default_config = {**definition["default_config"]}
    if domain == "domain_a":
        default_config["initials"] = initials
        default_config["tag_pattern"] = tag_pattern
    return build_generate_response(
        domain=domain,
        name=definition["name"],
        description=definition["summary"],
        transformation_summary=list(definition["transformation_summary"]),
        trigger_prompt=definition["default_prompt"],
        ui_prefs={
            "theme": theme,
            "density": density,
            "primary_label": definition["primary_label"],
        },
        default_config=default_config,
    )


def render_domain_tool(
    *,
    domain: DomainKey,
    name: str,
    description: str,
    theme: str,
    density: str,
    default_config: dict[str, Any],
) -> str:
    if domain == "domain_a":
        return _render_domain_a_tool(name=name, description=description, theme=theme, density=density, default_config=default_config)
    if domain == "domain_b":
        return _render_domain_b_tool(name=name, description=description, theme=theme, density=density, default_config=default_config)
    return _render_domain_c_tool(name=name, description=description, theme=theme, density=density, default_config=default_config)


def _shell_header(name: str, description: str, theme: str, density: str) -> tuple[str, dict[str, str], str]:
    palette = corporate_palette(theme)
    padding = "20px" if density == "comfortable" else "14px"
    return padding, palette, f"""
<!DOCTYPE html>
<html lang="en" data-theme="{theme}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{name}</title>
    <style>
      :root {{
        color-scheme: {palette["color_scheme"]};
        --bg: {palette["background"]};
        --surface: {palette["surface"]};
        --fg: {palette["foreground"]};
        --muted: {palette["muted"]};
        --accent: {palette["accent"]};
        --accent-soft: {palette["accent_soft"]};
        --border: {palette["border"]};
        --pad: {padding};
      }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--fg);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      main {{
        max-width: 920px;
        margin: 0 auto;
        padding: 40px 24px 56px;
      }}
      .shell {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
        overflow: hidden;
      }}
      header {{
        padding: 24px;
        border-bottom: 1px solid var(--border);
      }}
      h1 {{
        margin: 0 0 8px;
        font-size: 1.9rem;
        letter-spacing: -0.02em;
      }}
      p {{
        margin: 0;
        color: var(--muted);
      }}
      .body {{
        display: grid;
        gap: 16px;
        padding: 24px;
      }}
      textarea, pre {{
        width: 100%;
        box-sizing: border-box;
        min-height: 180px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--surface) 92%, var(--bg));
        color: var(--fg);
        padding: var(--pad);
        font: inherit;
      }}
      pre {{
        overflow: auto;
        white-space: pre-wrap;
      }}
      .actions {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }}
      button {{
        border: 0;
        border-radius: 999px;
        padding: 11px 16px;
        font-weight: 700;
        cursor: pointer;
      }}
      .primary {{
        background: var(--accent);
        color: #ffffff;
      }}
      .secondary {{
        background: transparent;
        color: var(--fg);
        border: 1px solid var(--border);
      }}
      .status {{
        color: var(--muted);
        font-size: 0.95rem;
      }}
      .panel {{
        border: 1px solid var(--border);
        border-radius: 14px;
        background: var(--accent-soft);
        padding: 16px;
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="shell">
        <header>
          <h1>{name}</h1>
          <p>{description}</p>
        </header>
        <div class="body">
"""


def _shell_footer(script: str) -> str:
    return f"""
        </div>
      </section>
    </main>
    {script}
  </body>
</html>
"""


def _render_domain_a_tool(*, name: str, description: str, theme: str, density: str, default_config: dict[str, Any]) -> str:
    cdn_registry = json.loads(CDN_REGISTRY_PATH.read_text(encoding="utf-8"))
    script = f"""
<script src="{cdn_registry["papaparse"]}"></script>
<script src="{cdn_registry["sheetjs"]}"></script>
<script>
  const TOOL_METADATA = {json.dumps({
        "id": "tool_lead_formatter_generated_v1",
        "name": name,
        "version": "1.0",
        "input_type": "csv_string",
        "output_type": "xlsx_blob",
    })};
  const TOOL_DEFAULT_CONFIG = {json.dumps(default_config)};
  const STAGE_RANK = {{ seed: 0, series_a: 1, series_b: 2, series_c: 3, series_d: 4, ipo: 5 }};
  function parseCsv(text) {{
    if (window.Papa && text.trim()) {{
      return window.Papa.parse(text.trim(), {{ skipEmptyLines: true }}).data;
    }}
    return String(text || "").trim().split(/\\r?\\n/).filter(Boolean).map((line) => line.split(","));
  }}
  function buildPreviewRows(input, config) {{
    const rows = parseCsv(String(input || ""));
    if (!rows.length) return [];
    const [header, ...body] = rows;
    const index = Object.fromEntries(header.map((name, position) => [String(name).trim().toLowerCase(), position]));
    const industryIndex = index["industry"];
    const stageIndex = index["stage"];
    const employeesIndex = index["employees"];
    const outputHeader = [...header, "tag"];
    const filtered = body
      .filter((row) => String(row[industryIndex] || "").toLowerCase().includes(String(config.industry || "fintech").toLowerCase()))
      .filter((row) => (STAGE_RANK[String(row[stageIndex] || "").trim().toLowerCase().replace(/\\s+/g, "_")] || 0) >= STAGE_RANK[config.filter_min_stage])
      .sort((left, right) => Number(right[employeesIndex] || 0) - Number(left[employeesIndex] || 0))
          .map((row) => {{
        const industryToken = String(row[industryIndex] || "Fintech").replace(/\\s+/g, "");
        const tag = String(config.tag_pattern || "[Q2-Outbound-{{industry}}-{{initials}}]")
          .replaceAll("{{industry}}", industryToken)
          .replaceAll("{{initials}}", String(config.initials || "BK").toUpperCase());
        return [...row, tag];
      }});
    return [outputHeader, ...filtered];
  }}
  window.Tool = {{
    metadata: TOOL_METADATA,
    defaultConfig: TOOL_DEFAULT_CONFIG,
    async transform(input, config = {{}}) {{
      const rows = buildPreviewRows(input, {{ ...TOOL_DEFAULT_CONFIG, ...config }});
      if (!rows.length) {{
        return new Blob([""], {{ type: "text/plain;charset=utf-8" }});
      }}
      const worksheet = window.XLSX.utils.aoa_to_sheet(rows);
      const workbook = window.XLSX.utils.book_new();
      window.XLSX.utils.book_append_sheet(workbook, worksheet, "Leads");
      const array = window.XLSX.write(workbook, {{ bookType: "xlsx", type: "array" }});
      return new Blob([array], {{ type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }});
    }}
  }};
  const inputArea = document.getElementById("input-area");
  const previewElement = document.getElementById("preview");
  const statusElement = document.getElementById("status");
  document.getElementById("preview-button").addEventListener("click", () => {{
    const rows = buildPreviewRows(inputArea.value, TOOL_DEFAULT_CONFIG);
    previewElement.textContent = rows.length ? rows.map((row) => row.join(" | ")).join("\\n") : "No matching rows yet.";
    statusElement.textContent = rows.length ? `Preview ready: ${{Math.max(rows.length - 1, 0)}} rows.` : "No matching rows yet.";
  }});
  document.getElementById("download-button").addEventListener("click", async () => {{
    const blob = await window.Tool.transform(inputArea.value);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "leads_formatted.xlsx";
    anchor.click();
    URL.revokeObjectURL(url);
    statusElement.textContent = "Download started.";
  }});
</script>
"""
    _, _, header = _shell_header(name, description, theme, density)
    body = """
          <label for="input-area">Paste the raw leads CSV</label>
          <textarea id="input-area" spellcheck="false" placeholder="company,industry,stage,employees,domain"></textarea>
          <div class="actions">
            <button class="secondary" id="preview-button">Preview Output</button>
            <button class="primary" id="download-button">Format My Leads</button>
          </div>
          <div class="status" id="status">Paste CSV rows, then preview or download.</div>
          <pre id="preview">Preview will appear here.</pre>
"""
    return header + body + _shell_footer(script)


def _render_domain_b_tool(*, name: str, description: str, theme: str, density: str, default_config: dict[str, Any]) -> str:
    script = f"""
<script>
  const TOOL_METADATA = {json.dumps({
        "id": "tool_market_brief_generated_v1",
        "name": name,
        "version": "1.0",
        "input_type": "json",
        "output_type": "html",
    })};
  const TOOL_DEFAULT_CONFIG = {json.dumps(default_config)};
  function buildBrief(input, config) {{
    const payload = JSON.parse(String(input || "{{}}"));
    const tickers = Array.isArray(payload.tickers) ? payload.tickers : [];
    const marketData = payload.market_data || {{}};
    const items = tickers.slice(0, config.max_points || 3).map((ticker) => {{
      const details = marketData[ticker] || {{}};
      return `<li><strong>${{ticker}}</strong>: price ${{details.price ?? "n/a"}}, market cap ${{details.market_cap ?? "n/a"}}.</li>`;
    }});
    return `<section><h3>${{config.heading}}</h3><p>Tone: ${{config.tone}}</p><ul>${{items.join("")}}</ul></section>`;
  }}
  window.Tool = {{
    metadata: TOOL_METADATA,
    defaultConfig: TOOL_DEFAULT_CONFIG,
    async transform(input, config = {{}}) {{
      return buildBrief(input, {{ ...TOOL_DEFAULT_CONFIG, ...config }});
    }}
  }};
  const inputArea = document.getElementById("input-area");
  const previewElement = document.getElementById("preview");
  document.getElementById("run-button").addEventListener("click", async () => {{
    try {{
      previewElement.textContent = await window.Tool.transform(inputArea.value);
    }} catch (error) {{
      previewElement.textContent = `Error: ${{error.message}}`;
    }}
  }});
</script>
"""
    _, _, header = _shell_header(name, description, theme, density)
    body = """
          <label for="input-area">Paste market JSON</label>
          <textarea id="input-area" spellcheck="false" placeholder='{"tickers":["AAPL"],"market_data":{"AAPL":{"price":194.11,"market_cap":"3.0T"}}}'></textarea>
          <div class="actions">
            <button class="primary" id="run-button">Build Brief</button>
          </div>
          <div class="panel">
            <strong>Expected input</strong>
            <p>JSON with <code>tickers</code> and <code>market_data</code>.</p>
          </div>
          <pre id="preview">Brief preview will appear here.</pre>
"""
    return header + body + _shell_footer(script)


def _render_domain_c_tool(*, name: str, description: str, theme: str, density: str, default_config: dict[str, Any]) -> str:
    script = f"""
<script>
  const TOOL_METADATA = {json.dumps({
        "id": "tool_reply_drafter_generated_v1",
        "name": name,
        "version": "1.0",
        "input_type": "json",
        "output_type": "text",
    })};
  const TOOL_DEFAULT_CONFIG = {json.dumps(default_config)};
  function buildReply(input, config) {{
    const payload = JSON.parse(String(input || "{{}}"));
    const ticket = payload.ticket || {{}};
    const customer = payload.customer || {{}};
    return [
      `Hi ${{customer.name || "there"}},`,
      "",
      `I'm sorry about the issue described in ticket ${{ticket.ticket_id || "unknown"}}.`,
      `I reviewed the note about "${{ticket.subject || "your request"}}" and I'm moving this forward with priority.`,
      `Because you're on the ${{customer.plan || "current"}} plan, I'll follow up as soon as I have the next update.`,
      "",
      config.signoff || "Best,\\nKai",
      `Tone: ${{config.tone || "calm and direct"}}`
    ].join("\\n");
  }}
  window.Tool = {{
    metadata: TOOL_METADATA,
    defaultConfig: TOOL_DEFAULT_CONFIG,
    async transform(input, config = {{}}) {{
      return buildReply(input, {{ ...TOOL_DEFAULT_CONFIG, ...config }});
    }}
  }};
  const inputArea = document.getElementById("input-area");
  const previewElement = document.getElementById("preview");
  document.getElementById("run-button").addEventListener("click", async () => {{
    try {{
      previewElement.textContent = await window.Tool.transform(inputArea.value);
    }} catch (error) {{
      previewElement.textContent = `Error: ${{error.message}}`;
    }}
  }});
</script>
"""
    _, _, header = _shell_header(name, description, theme, density)
    body = """
          <label for="input-area">Paste ticket + customer JSON</label>
          <textarea id="input-area" spellcheck="false" placeholder='{"ticket":{"ticket_id":"TICK-1"},"customer":{"name":"Jordan"}}'></textarea>
          <div class="actions">
            <button class="primary" id="run-button">Draft Reply</button>
          </div>
          <div class="panel">
            <strong>Expected input</strong>
            <p>JSON with <code>ticket</code> and <code>customer</code>.</p>
          </div>
          <pre id="preview">Draft preview will appear here.</pre>
"""
    return header + body + _shell_footer(script)

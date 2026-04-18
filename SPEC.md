# Personal Workflow Agent — Requirements & Architecture Spec

**Version:** v1.0 — hackathon build spec
**Duration:** 48-hour build
**Sponsor model:** MBZUAI K2-V2 (LLM360, 70B, OpenAI-compatible via vLLM)

---

## 0. TL;DR

A background browser agent observes how a worker transforms data during their routine, and automatically generates them a personal mini web-tool that performs just that transformation. The worker never records or teaches anything. When they visit a relevant site, a small popup appears: *"I built you a tool for this."* They click, drop their data in, get formatted output out.

We are not building browser automation. We are not building a chatbot. We are building a **personal tool factory** that captures the worker's idiosyncratic transformation logic — naming conventions, filtering rules, reply templates, tagging conventions — as self-contained HTML+JS artifacts. The architecture is designed so a future proactive agent can run these same tools on the worker's behalf without a rewrite.

---

## 1. Product Thesis

> The fundamental economics of labor are changing. A job isn't a monolith — it's a bundle of discrete tasks. AI executes tasks, not jobs. So the real productivity benchmark isn't "AI vs. Human," it's **"worker with AI" vs. "worker without AI."**
>
> But standardized AI platforms aren't delivering this productivity gain, because every worker has a highly idiosyncratic way of doing their tasks. Standardized tools create friction. Workers have to change their behavior to use them.
>
> We eliminate the friction by generating a **personal tool** for each worker's specific way of working — observed passively, built automatically, used contextually.

**Two sentences for the pitch deck:**
1. *Browser automation records where a worker clicks. A personal tool encodes how they think.*
2. *When the source site changes, automation breaks. A personal tool keeps working — because it operates on data, not on clicks.*

**What we are explicitly NOT building (and why):**

| Not this | Why |
|----------|-----|
| A chatbot | Chat is high-friction and not the form factor workers want for repeated tasks |
| A browser-automation agent that replays click sequences | Brittle; breaks on DOM change; duplicates what Zapier/Operator already do |
| A workflow recorder ("click here to teach it") | Adds friction; the professor's core point is that friction kills adoption |
| A generic SaaS platform | The value is in personalization; generic tools cannot capture it |

---

## 2. What The Worker Experiences

**Bob — sales rep. Morning, day 3 with the extension installed.**

1. Bob opens his browser, visits `portal.example.com/leads`, as he has every morning.
2. A small toast slides in at the bottom right: *"I noticed you format lead exports every morning. I made you a Lead List Formatter. [Open tool] [Not now]."*
3. Bob clicks Open. A new tab opens: dark mode, compact, one big drop zone: "Drop your lead CSV or paste it here."
4. Bob exports the CSV from the portal, drags it into the drop zone.
5. The tool preview shows: filtered Series B+ fintech leads, sorted by headcount, tag column auto-populated with `[Q2-Outbound-Fintech-BK]`.
6. Bob clicks "Download XLSX." Done. The file matches the exact format his manager expects.

What Bob didn't do: train anything, record anything, write any config, click any setup wizard. The extension simply watched him do this manually two or three times in prior days and generated the tool while he wasn't looking.

**What this feels like as a product: a thoughtful assistant who quietly builds you a small custom tool every time they notice you've built a habit.**

---

## 3. Architectural Principles

Seven principles that guide every design decision in this document.

1. **Observation is passive. Generation is automatic. Use is contextual.** No explicit recording, no setup wizards, no prompts to the user. The worker sees one thing only: the popup, when it's relevant.
2. **Tools, not automations.** Generated artifacts operate on data the worker provides, not on the source websites. No Playwright, no click-replay, no selector fragility.
3. **The tool is a pure function + a UI.** Every tool exposes both a programmatic `transform(input, config) → output` interface AND a human UI. This is how we become agent-ready later.
4. **Contracts are public. Implementations are private.** Teams interact through the schemas in §11 and the endpoints in §12 only. No cross-service imports.
5. **Trigger type is a tagged union from day one.** v1 ships `on_url_visit`. v2 adds `on_schedule`, `on_email_received`, etc. Adding a trigger type never requires schema changes.
6. **Caching is the production path, not a fallback.** Every live AI call produces a cached artifact. If K2-V2 is down during demo, we serve cache transparently.
7. **The worker is always in control.** Tools open on click, not autoplay. Even the future proactive agent surfaces results for review before taking irreversible action.

---

## 4. System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                      Chrome Extension (Plasmo + React)                │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────────┐   │
│  │ rrweb        │   │ Event Batcher    │   │ In-Page Popup        │   │
│  │ recorder     │──▶│ (60s windows,    │   │ + Tool Launcher      │   │
│  │ + clipboard  │   │  clipboard data) │   │ + Feedback capture   │   │
│  └──────────────┘   └────────┬─────────┘   └──────────┬───────────┘   │
└────────────────────────────┬─┼──────────────────────┬─┼───────────────┘
                             │ │ POST /v1/events      │ │ GET /v1/tools/for_url
                             │ │ POST /v1/feedback    │ │ GET /v1/tools/:id/artifact
                             │ ▼                      │ ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       Backend Core (FastAPI)                          │
│                                                                       │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────────────┐  │
│  │ Event Store    │  │ Tool Registry   │  │ Artifact Store         │  │
│  │ (SQLite)       │  │ (SQLite)        │  │ (blob: HTML + config)  │  │
│  └────────┬───────┘  └────────┬────────┘  └──────────┬─────────────┘  │
│           │                   │                      │                │
│           ▼                   ▼                      │                │
│  ┌──────────────────────┐  ┌──────────────────────┐  │                │
│  │ Detection Scheduler  │  │ Trigger Evaluator    │  │                │
│  │ (periodic loop)      │  │ ─ on_url_visit  (v1) │  │                │
│  │                      │  │ ─ on_schedule   (v2) │  │                │
│  │                      │  │ ─ on_email      (v2) │  │                │
│  └──────────┬───────────┘  └──────────────────────┘  │                │
│             │                                        │                │
│             │         ┌──────────────────────────┐   │                │
│             │         │ Tool Orchestrator  (stub)│◀──┘                │
│             │         │ calls tools programmatic-│                    │
│             │         │ ally — used by future    │                    │
│             │         │ proactive agent          │                    │
│             │         └──────────────────────────┘                    │
└─────────────┼─────────────────────────────────────────────────────────┘
              │ POST /ai/detect_transformation
              │ POST /ai/generate_tool
              ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      AI Pipeline Service                              │
│  ┌───────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │ K2-V2 client      │  │ Prompt library   │  │ Mem0 preferences  │   │
│  │ (OpenAI-compat)   │  │ (versioned)      │  │ (per user_id)     │   │
│  │ reasoning_effort: │  │ — detect.py      │  └───────────────────┘   │
│  │   med / high      │  │ — generate.py    │  ┌───────────────────┐   │
│  └───────────────────┘  └──────────────────┘  │ Primitive registry│   │
│                                               │ (whitelisted JS   │   │
│                                               │  libs for tools)  │   │
│                                               └───────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

### Component summary

| Component | Purpose | Owner |
|-----------|---------|-------|
| Chrome extension | Observe events, show popup, launch tools | Team A |
| Event store | Ring buffer of recent events per user | Team B |
| Tool registry | Canonical list of generated tools | Team B |
| Artifact store | Blob storage for generated HTML tools | Team B |
| Detection scheduler | Periodically triggers AI detection on recent events | Team B |
| Trigger evaluator | Decides which tools apply to a URL (and later: time, email, etc.) | Team B |
| Tool orchestrator | Calls tools programmatically; stub in v1, real in v2 | Team B (stub) |
| AI pipeline | K2-V2 integration, prompts, Mem0, primitive registry | Team C |
| Tool runtime | Shared JS primitives + tool shell template | Team D |
| Demo fixtures | Sample source data, mock sites, seed event traces | Team D |

---

## 5. The Tool — Central Object

A generated tool is the central artifact of this product. Everything else exists to produce it or help the worker discover it.

### 5.1 What a generated tool is

A **single self-contained HTML file** containing:
- A minimal UI (drop zone, paste area, preview, output button) styled per the worker's `ui_prefs`
- Embedded JavaScript implementing the worker's specific transformation logic
- Primitive JS libraries loaded from a whitelisted CDN (Papaparse, SheetJS, Luxon, Mustache, Marked)
- **A programmatic interface:** `window.Tool = { transform(input, config), metadata }`

### 5.2 The programmatic interface (agent-ready design)

Every generated tool MUST expose a global `window.Tool` object with this shape:

```javascript
window.Tool = {
  metadata: {
    id: "tool_lead_formatter_v1",
    name: "Lead List Formatter",
    version: "1.0",
    input_type: "csv_string" | "text" | "json" | "file",
    output_type: "xlsx_blob" | "csv_string" | "text" | "html"
  },

  // Pure function. Same input + config always produces same output.
  // Never reads DOM, never touches UI. Called by both UI and future agent.
  async transform(input, config = {}) {
    // ... worker's specific logic ...
    return output;
  },

  // Optional: default config captured from observation
  defaultConfig: {
    tag_pattern: "[Q2-Outbound-{industry}-{initials}]",
    filter_min_stage: "series_b",
    sort_by: "employees_desc"
  }
};
```

**Why this matters:** In v1, the UI calls `window.Tool.transform()` when the worker clicks the button. In v2, a proactive agent running headlessly can load the same HTML artifact in a background iframe (or evaluate the JS in a sandbox) and call `window.Tool.transform()` directly with data it fetched on the worker's behalf. Zero rewrite.

The generation prompt explicitly enforces this interface. See §13.2.

### 5.3 Tool registry record (JSON schema)

```json
{
  "id": "tool_lead_formatter_v1",
  "user_id": "bob",
  "name": "Lead List Formatter",
  "description": "Drop your lead CSV; get a filtered, tagged, CRM-ready XLSX.",
  "created_at": "2026-04-18T09:00:00Z",

  "source_event_window": {
    "start": "2026-04-17T09:00:00Z",
    "end": "2026-04-17T09:20:00Z",
    "repetition_count": 3
  },

  "trigger": {
    "type": "on_url_visit",
    "url_pattern": "*.portal.example.com/leads*",
    "time_window": {
      "start": "08:00",
      "end": "10:30",
      "timezone": "America/New_York"
    },
    "prompt": "Ready to format today's leads?"
  },

  "transformation_summary": [
    "Input: CSV of raw leads",
    "Filter to Series B+ in fintech",
    "Sort by company size descending",
    "Add tag column [Q2-Outbound-Fintech-{initials}]",
    "Output: XLSX for CRM import"
  ],

  "artifact": {
    "type": "html_single_file",
    "version": "1.0",
    "artifact_id": "art_ab12cd34",
    "input_spec": {
      "primary_input": "csv_file",
      "accepts": ["paste", "file_drop", "file_picker"],
      "sample_fixture_id": "fixture_leads_sample"
    },
    "output_spec": {
      "format": "xlsx",
      "filename_pattern": "leads_{YYYY-MM-DD}.xlsx"
    },
    "primitives_used": ["papaparse", "sheetjs"],
    "programmatic_interface": {
      "input_type": "csv_string",
      "output_type": "xlsx_blob"
    }
  },

  "ui_prefs": {
    "theme": "dark",
    "density": "compact",
    "primary_label": "Format My Leads",
    "show_preview": true
  },

  "stats": {
    "times_used": 0,
    "last_used": null,
    "avg_duration_ms": null
  },

  "status": "ready"
}
```

Allowed `status`: `generating | ready | needs_review | disabled | failed`.
Allowed `trigger.type` (v1): `on_url_visit`. Reserved for v2: `on_schedule`, `on_email_received`, `on_calendar_event`, `on_file_created`.

---

## 6. Agent-Ready Architecture (Explicit)

This section documents exactly how v2 proactive-agent capability bolts onto v1 without a rewrite. Each team references this to ensure their v1 choices don't foreclose v2.

### 6.1 What v2's proactive agent does

- Watches execution history patterns (Bob opens Lead Formatter every weekday 9:10–9:15am)
- 2 minutes before the predicted time, pre-fetches relevant data (if Bob has given permission — e.g., via an email/calendar MCP connector)
- Calls `Tool.transform(data, defaultConfig)` directly via the Tool Orchestrator
- Surfaces the result in a notification: *"Your formatted leads are ready. Review."*
- Bob clicks review → sees the output → approves or edits

The worker stays in the loop. The agent is a time-saver, not a replacement.

### 6.2 What must be true in v1 for this to work in v2

| Agent v2 capability | v1 requirement that enables it |
|---|---|
| Run tools without UI | Every tool exposes `window.Tool.transform()` pure function (§5.2) |
| Detect time patterns | Every tool invocation logs to `stats` in registry (§5.3); execution history queryable |
| Add new trigger types | Trigger is tagged union; evaluator is pluggable (§4) |
| Orchestrate tool calls | Tool Orchestrator exists as a stub service in v1 with one method: `run_tool(tool_id, input_data)` (§12.4) |
| Fetch data autonomously | Out of scope for v1; no v1 code will block this (v2 adds MCP connectors to Backend Core) |
| Notify without stealing focus | Popup already exists (§9); v2 reuses it for "tool ran on your behalf" notifications |

### 6.3 Tool Orchestrator stub (ships in v1)

```python
# /backend/app/orchestrator.py
class ToolOrchestrator:
    """
    v1: Only used for internal testing and as a deployment target for v2.
    v2: Called by scheduler, email watcher, calendar watcher.
    Exposes a stable contract so v2 can swap in new triggers without
    touching the execution path.
    """
    async def run_tool(
        self,
        tool_id: str,
        input_data: Any,
        config_override: dict | None = None,
    ) -> ToolRunResult:
        tool = self.registry.get(tool_id)
        artifact = self.artifact_store.get(tool.artifact_id)
        # v1: runs via headless Chromium evaluating window.Tool.transform
        # v2: same code path, triggered by scheduler instead of HTTP request
        return await self._evaluate_in_sandbox(artifact, input_data, config_override)
```

In v1, this method is implemented but only called by internal test endpoints. In v2, it's called by the scheduler.

---

## 7. Observation Layer

The extension's job is to capture a faithful record of what the worker did in the browser — with special attention to the data flowing through their work, not just their clicks.

### 7.1 Event capture priorities

**Tier 1 (critical — these reveal transformations):**
- `copy` events with clipboard contents (truncated to 5KB)
- `paste` events with pasted contents (truncated to 5KB)
- `input` events with field values
- `submit` events

**Tier 2 (useful — these reveal context):**
- `navigation` events (URL transitions)
- `click` events with target text and ARIA label

**Tier 3 (stripped for privacy + payload size):**
- Mouse coordinates
- Hover events
- Scroll events (aggregate only: final `scroll_y` at page leave)
- Keystrokes on password fields (never captured)

### 7.2 Privacy & sensitive data

Extension MUST NOT capture:
- Any input on fields with `type="password"` or `autocomplete="cc-*"` or `autocomplete="*-name"` that matches known payment-card regex
- Content from URLs matching a user-configurable denylist (default includes common banking, medical, dating sites)

This is a v1 requirement. Don't ship without it.

### 7.3 Event batching

- Events accumulate in the extension's service worker
- Flushed every 60 seconds OR when buffer reaches 500 events, whichever first
- POSTed to `/v1/events` in batches
- On network failure: retry with exponential backoff, max 3 attempts, then drop

---

## 8. Detection Pipeline

### 8.1 Trigger cadence

Backend Core's detection scheduler runs a loop per user:

1. Every 2 minutes, check if new events have accumulated since last detection
2. If ≥ 50 new events OR ≥ 10 minutes of activity: compress events, call `/ai/detect_transformation`
3. If detected: call `/ai/generate_tool`, store artifact, add to registry with status `ready`
4. Never re-detect a transformation whose signature is already in the registry

### 8.2 What "detected" means

A transformation is a sequence where:
- The worker brought data *in* (copy, file drop, paste, export click)
- Did some manipulation (edits, pastes into a template)
- Produced data *out* (download, paste into a destination field, submit)
- Did it **2 or more times** with similar shape

The detection prompt is explicit about this — it's looking for data-flow repetition, not click-sequence repetition.

---

## 9. Popup & Tool Experience

### 9.1 Popup trigger

On every page navigation, the content script calls `GET /v1/tools/for_url`. If any tool matches:

1. Wait 2 seconds (don't interrupt mid-action)
2. Slide in a small toast, bottom-right corner, 320px wide
3. Content:
   - Icon (small, theme-matched)
   - One-line prompt (from `trigger.prompt` field)
   - Two buttons: "Open tool" (primary), "Not now" (secondary)
   - Tiny "×" to dismiss + "don't suggest here again" option in a menu
4. Auto-dismiss after 20 seconds if no interaction

### 9.2 Opening the tool

- "Open tool" triggers `chrome.tabs.create({ url: '/v1/tools/{id}/artifact' })`
- The tool loads as a standalone page — full HTML, styled per `ui_prefs`
- Tool runs in browser; no server calls beyond the initial GET

### 9.3 Feedback capture

Every tool page has a small footer with:
- "Works well" / "Something's off" buttons
- A text field for free-form feedback ("make it dark mode", "tag should say Q3 not Q2", "add a total row")

Any feedback → `POST /v1/feedback` → stored in Mem0 → affects next generation.

### 9.4 Library view (minimal)

Clicking the extension icon opens a small popup listing the worker's generated tools. Each row: name, last used, [Open] button. This is NOT a separate app; it's a 100-line React popup. Discoverability only.

---

## 10. Preference Memory (Mem0)

- Self-hosted Mem0 via Docker
- One user_id per worker
- Preferences retrieved before every generation call, not before detection
- Feedback stored immediately on `/v1/feedback`

```python
# Before every /ai/generate_tool call:
prefs = mem0_client.search(
    query="UI and transformation preferences",
    user_id=user_id,
    limit=10
)
prefs_block = "\n".join(p["memory"] for p in prefs)
# Injected into the generation prompt's "User preferences" section.
```

Embedding model: use a small local sidecar (e.g., `all-MiniLM-L6-v2` via `sentence-transformers`). Don't use K2-V2 for embedding — wrong tool, too heavy.

---

## 11. Data Contracts (Schemas)

The two central schemas. Change only by group agreement.

### 11.1 Event

```json
{
  "session_id": "sess_abc123",
  "user_id": "bob",
  "timestamp": "2026-04-18T09:01:23.456Z",
  "url": "https://portal.example.com/leads",
  "event_type": "copy",
  "target": {
    "tag": "td",
    "role": null,
    "text": "Acme Corp",
    "aria_label": null
  },
  "value": "Acme Corp,Fintech,Series B,85,acme.com\nBeta Inc,Fintech,Series A,20,beta.io",
  "metadata": {
    "viewport": [1440, 900]
  }
}
```

Allowed `event_type`: `click | input | navigation | copy | paste | submit | select | file_download`.

### 11.2 Tool

See §5.3 — the canonical definition.

---

## 12. API Contracts

All JSON. Errors: `{"error": {"code": "...", "message": "..."}}`. Timestamps ISO 8601 UTC.

### 12.1 Extension → Backend Core

**`POST /v1/events`** — batch event upload
Request: `{"user_id": "bob", "events": [<Event>, ...]}`
Response: `{"accepted": 47, "buffered": 312}`

**`GET /v1/tools/for_url?url={url}&user_id={id}`**
Response: `{"tools": [<Tool>, ...]}`
Returns tools whose trigger matches URL + current time window.

**`GET /v1/tools/{id}/artifact`**
Response: `Content-Type: text/html`; body is the full tool HTML. Opened in a new tab.

**`POST /v1/tools/{id}/usage`** — tool was used
Request: `{"user_id": "bob", "succeeded": true, "duration_ms": 12000}`
Response: `{"logged": true}`

**`POST /v1/feedback`**
Request: `{"user_id": "bob", "tool_id": "tool_...", "feedback": "make it dark mode", "context": "ui"}`
Response: `{"stored": true, "memory_id": "mem_..."}`

### 12.2 Backend Core → AI Pipeline

**`POST /ai/detect_transformation`**
Request: `{"user_id": "bob", "events": [...], "existing_tool_signatures": ["sig_abc"]}`
Response:
```json
{
  "detected": true,
  "signature": "sig_ghi789",
  "confidence": 0.87,
  "transformation_name": "Lead List Formatter",
  "summary": "...",
  "input_characterization": "...",
  "output_characterization": "...",
  "event_window": {"start": "...", "end": "..."},
  "repetition_count": 3
}
```
Or: `{"detected": false}`

**`POST /ai/generate_tool`**
Request: `{"user_id": "bob", "detection": {...}, "events": [...], "user_prefs_hint": "..."}`
Response:
```json
{
  "name": "Lead List Formatter",
  "description": "...",
  "transformation_summary": ["..."],
  "html_artifact": "<!DOCTYPE html>...",
  "input_spec": {"primary_input": "csv_file", "accepts": ["paste", "file_drop", "file_picker"]},
  "output_spec": {"format": "xlsx", "filename_pattern": "leads_{YYYY-MM-DD}.xlsx"},
  "trigger": {"type": "on_url_visit", "url_pattern": "...", "prompt": "..."},
  "ui_prefs": {...},
  "primitives_used": ["papaparse", "sheetjs"],
  "programmatic_interface": {"input_type": "csv_string", "output_type": "xlsx_blob"}
}
```

### 12.3 Backend internal (artifacts)

**`POST /internal/artifacts`** → `{"artifact_id": "art_..."}`
**`GET /internal/artifacts/{id}`** → raw HTML

### 12.4 Tool Orchestrator (stub in v1, real in v2)

**`POST /internal/orchestrator/run_tool`**
Request: `{"tool_id": "...", "user_id": "bob", "input_data": "...", "config_override": {}}`
Response: `{"run_id": "...", "output_ref": "blob_id or inline", "succeeded": true}`

In v1: implemented and tested; only called by internal test endpoints. In v2: called by scheduler, email watcher, etc.

---

## 13. LLM Prompt Contracts (with actual prompt text)

### 13.1 Detection prompt (K2-V2)

**System prompt:**
```
You are a data-transformation pattern detector. You are given a compressed
sequence of browser events for a single user over a bounded time window.
Each event includes timestamp, URL, event type, target element, and — for
copy/paste/input events — the actual text content.

Your job: identify whether the user performed the same data transformation
at least TWICE during this window. Focus on the DATA FLOW, not the click
sequence. A transformation has three phases:
  (1) Data acquisition (copy from a source, file download, form read)
  (2) Manipulation (filter, reformat, annotate, template-fill)
  (3) Data delivery (paste to destination, download, submit)

Output strict JSON matching the schema. If unsure, return {"detected": false}.
Being wrong about detection is more expensive than missing a real pattern.
```

**User prompt template:**
```
USER ID: {user_id}
WINDOW: {start} → {end}
EXISTING TOOL SIGNATURES (do NOT re-detect): {signatures}

EVENTS:
{compressed_event_list}

OUTPUT (strict JSON):
{detection_schema}
```

**K2-V2 settings:** `reasoning_effort: medium`, `temperature: 0.3`, JSON mode on.

### 13.2 Tool generation prompt (K2-V2)

**System prompt:**
```
You generate personalized micro-tools as self-contained HTML files.

You will receive:
  1. A detected data transformation (input shape, output shape, logic summary)
  2. The worker's user_id and captured preferences (UI theme, conventions)
  3. A whitelist of JavaScript primitive libraries available via CDN

You will produce a single HTML file that:
  - Accepts input matching the input_spec (paste, file drop, or file picker)
  - Applies the worker's specific transformation logic — HARDCODE their
    conventions (tag patterns, column names, filter rules, template wording)
  - Produces output matching the output_spec
  - Displays a preview before export/copy
  - Styles itself according to the worker's ui_prefs

HARD REQUIREMENTS:
  - Single HTML file. All CSS and JS inline or via whitelisted CDN.
  - MUST expose a global `window.Tool` object with this exact shape:
      window.Tool = {
        metadata: { id, name, version, input_type, output_type },
        transform: async function(input, config) { ... return output; },
        defaultConfig: { ... }
      }
    This is non-negotiable. The UI's run button must call window.Tool.transform().
  - The transform() function must be PURE: same input + config → same output.
    It must not read the DOM, touch window state, or depend on UI.
  - No external API calls, no fetch() to arbitrary URLs. Only whitelisted CDN.
  - Handle empty / malformed input gracefully (show user-friendly error).

WHITELISTED CDN LIBRARIES:
{primitive_library_json}

Output strict JSON matching the schema.
```

**User prompt template:**
```
DETECTED TRANSFORMATION:
{detection_result}

RECENT EVENT TRACE (for reference on specific values like tag conventions):
{relevant_events_excerpt}

USER PREFERENCES (from Mem0):
{prefs_block}

OUTPUT (strict JSON):
{generation_schema}
```

**K2-V2 settings:** `reasoning_effort: high`, `temperature: 0.2`, JSON mode on.

K2-V2 is specifically optimized for code generation and instruction-following; this is the right model for this step.

### 13.3 Prompt fixtures

Team C commits `/ai/fixtures/` with triplets per domain:
- `domain_a_events.json` — realistic event trace
- `domain_a_detection.json` — target detector output
- `domain_a_tool.json` — target generator output (with full HTML string)

Same for domains B and C. These unblock parallel development.

---

## 14. Team Ownership

Four parallel tracks. Each team owns a directory and an API surface.

| Team | Directory | API surface they own | Deliverables |
|------|-----------|----------------------|--------------|
| **A. Extension** | `/extension` | Consumer of §12.1 | Plasmo + rrweb + clipboard capture + event batcher + popup UI + library view |
| **B. Backend Core** | `/backend` | Provides §12.1, §12.3, §12.4; consumes §12.2 | FastAPI + SQLite + registry + artifact store + detection scheduler + trigger evaluator + orchestrator stub |
| **C. AI Pipeline** | `/ai` | Provides §12.2 | K2-V2 client + prompts + Mem0 wrapper + primitive registry + fixtures |
| **D. Runtime + Fixtures** | `/runtime`, `/fixtures` | Publishes primitive library spec | JS primitives + tool shell template + sample CSVs / tickets / data + optional lightweight source-site mocks for demo |

**Interaction rule (repeat it aloud):** *I talk to other teams through §11 and §12 only. I do not import their code. If I need to change §11 or §12, I Slack the whole team first.*

---

## 15. 48-Hour Build Plan

Critical path in **bold**. Day 1 = hours 0–24, Day 2 = hours 24–48.

### Day 1 morning (hours 0–6)
- **[B]** FastAPI skeleton. SQLite schemas. Stub all §12 endpoints returning fixture responses.
- **[A]** Plasmo extension skeleton. rrweb integration. Verify clipboard capture in MV3 on demo laptop.
- **[C]** K2-V2 endpoint connection test. Write fixture triplets for Domain A. Verify JSON output shape end-to-end on one toy transformation.
- **[D]** Publish primitive library list + CDN URLs. Build tool shell template (header, drop zone, preview, output button, footer feedback bar). Commit one sample CSV fixture.

**Checkpoint 1 (h6): Each team's piece runs in isolation. Backend serves fixture tools. Extension captures clipboard contents on copy. AI pipeline generates valid HTML for a toy transformation. Tool shell renders correctly in a browser.**

### Day 1 afternoon (hours 6–14)
- **[A]** Event batcher + `/v1/events` end-to-end with real clipboard capture. Denylist logic for privacy.
- **[B]** Real event storage. `/v1/tools/for_url` + `/v1/tools/{id}/artifact` serving real HTML. Trigger evaluator for `on_url_visit`.
- **[C]** Detection prompt stabilized on Domain A fixtures. Iterate until detection is reliable across 5+ test traces.
- **[D]** Demo fixtures for all 3 domains (leads CSV, analyst tickers + data, support ticket + customer JSON). Optional: lightweight source-site mock at `portal.example.com` that serves a CSV download.

**Checkpoint 2 (h14): END-TO-END PATH WORKS WITH HAND-AUTHORED TOOLS. Extension records → backend stores → trigger matches → popup appears → worker clicks → generated HTML tool opens in new tab → worker drops data → transformation runs. This MUST work before AI goes into the loop.**

### Day 2 morning (hours 14–24)
- **[C]** Generation prompt stable. Produces working HTML tools for Domain A, then B, then C. Iterate against fixtures.
- **[B]** Wire auto-detection loop. Every 2 min call `/ai/detect_transformation`; if hit call `/ai/generate_tool`; store artifact + registry record.
- **[A]** Popup UX polish: slide-in animation, respects `ui_prefs.theme` from tool record for consistency, feedback capture in tool footer, library view in extension icon.
- **[D]** Verify generated tools work with demo fixtures. Write cached-tool fallbacks for demo safety.

**Checkpoint 3 (h24): Full auto loop works LIVE for Domain A. Domains B and C work with pre-seeded tools.**

### Day 2 afternoon (hours 24–36)
- **[All]** Pre-generate cached tools for all 3 domains as demo-day safety net.
- **[All]** Implement silent-fallback path: if K2-V2 call times out, backend returns cached tool.
- **[All]** Rehearse the 4-minute demo — 5+ full run-throughs.
- **[B or A]** Slide deck: 3-domain story + architecture diagram + v2 agent roadmap.

### Day 2 evening (hours 36–48)
- Reserved for the things that broke.

---

## 16. Demo Day Playbook

### 16.1 Pitch structure (4 minutes)

| Time | Slide / action | Content |
|------|---------------|---------|
| 0:00–0:30 | Slide: Bob at his desk | "Bob spends 20 minutes every morning formatting lead exports. His company bought an AI platform. It doesn't help — because his tagging convention is `[Q2-Outbound-Fintech-BK]`, and no platform knows that." |
| 0:30–1:00 | Slide: Professor's thesis | Economic framing. AI vs. human is the wrong benchmark. Worker-with-AI vs. worker-without-AI is the right one. Friction is what blocks it. |
| 1:00–1:15 | Slide: Our insight | *Personal tools, not browser automation. We encode how the worker thinks, not where they click.* |
| 1:15–2:45 | **LIVE Domain A** | Visit mock portal → popup slides in → click Open → tool opens dark-mode → drag sample CSV → preview shows formatted output with Bob's exact tag convention → download XLSX → open in Excel. ~90 seconds. |
| 2:45–3:15 | Slide: Domain B | Screenshot of Maya's analyst tool. Same mechanism, different transformation. |
| 3:15–3:40 | Slide: Domain C | Screenshot of Kai's reply drafter. **Emphasize this one** — the tool encodes his personal communication style, which is the most visible demonstration of the thesis. |
| 3:40–4:00 | Slide: v2 roadmap | Architecture already supports proactive agent: same tools, new trigger types, same `window.Tool.transform()` interface. Not a rewrite — an extension. |

### 16.2 Demo-day technical checklist

- [ ] All 3 tools pre-generated and in registry
- [ ] Silent-fallback tested: disconnect K2-V2 → demo still works
- [ ] Extension loaded and tested on demo laptop specifically
- [ ] Clipboard permissions granted on demo laptop
- [ ] Mock source site running on localhost
- [ ] Sample CSV pre-downloaded to Desktop
- [ ] Browser zoom level sensible for projector (usually 125%)
- [ ] Dev tools console CLOSED (distracting + may reveal errors)
- [ ] Dark desktop wallpaper (tools are dark mode; matches visually)

### 16.3 What to say if K2-V2 is live and works

*"The tool you just saw was generated by K2-V2 while I was walking on stage. The observation trace came from the last time I did this task, two days ago."*

### 16.4 What to say if you fall back to cache

Don't say anything. It's indistinguishable.

### 16.5 Judge Q&A — prepared answers

- **"Isn't this just Zapier?"** — Zapier moves data between apps on fixed schemas. We generate a personal tool whose logic is learned from observation and whose output matches the worker's idiosyncratic format. Zapier can't write the Playwright for `[Q2-Outbound-Fintech-BK]`; we can, because we watched Bob do it.
- **"How is this different from an AI browser agent like Operator?"** — Browser agents replay clicks and break when sites change. We generate tools that operate on data, so they don't depend on any specific website's DOM. The tool keeps working when the portal redesigns.
- **"What about privacy — you're recording everything?"** — Everything stays local to the worker's machine (or their company's instance). We strip password fields, denylist sensitive sites, and truncate clipboard contents. No data leaves their control.
- **"What's your moat?"** — Observation quality + Mem0 personalization + a library of tools that improves with use. Every tool generated for a worker is *theirs*, not ours — we are the tool factory, not the toolmaker.
- **"How does this scale to more complex workflows?"** — Composition is a v2 trigger type: `on_tool_completed`. Tool A finishes → triggers tool B. Because every tool has a programmatic interface, the composition is just `await ToolB.transform(await ToolA.transform(input))`.

---

## 17. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| K2-V2 latency too slow for live generation (>30s) | High | Pre-generate all demo tools; silent fallback to cache; use `reasoning_effort: medium` for detection loop |
| Generated HTML tool has JS bugs | Medium | Team D tests generated tools against fixtures at checkpoint 3; generation prompt includes "handle empty/malformed input gracefully" constraint |
| Detection prompt false positives | Medium | Require `repetition_count ≥ 2`; 3+ few-shot examples in prompt; "return detected:false if unsure" in system prompt |
| Chrome MV3 clipboard permissions | Medium | Tested on demo laptop day 1; manifest permissions verified |
| Mem0 preferences not reflected in generation | Low | Log exact prompt context per AI call; Team C writes a feedback → regenerate integration test |
| Demo laptop network fails | Low | Everything localhost; K2-V2 only needed for fresh generation; cached tools work offline |
| K2-V2 endpoint down during demo | Medium | Cached tools = fully functional demo with zero live AI calls |
| Worker privacy concern in pitch | Low-medium | Have denylist + password-field logic ready to show judges if asked |
| Tools expose `window.Tool` but generator sometimes forgets | Medium | Post-generation validation step: parse HTML, verify `window.Tool.transform` exists; if not, reject and regenerate once |

---

## 18. v2 Roadmap (Closing Slide Material)

Each item reuses v1 infrastructure; none require a rewrite.

1. **Proactive scheduler** — adds `on_schedule` trigger type. Scheduler watches `stats.last_used` patterns across the registry, predicts upcoming invocations, pre-calls `Tool.transform()` via the Orchestrator. Notifications use the existing popup system.
2. **External data sources (MCP connectors)** — Backend Core gains MCP client capability for Gmail, Calendar, Slack, Drive. The agent can fetch input data for tools on the worker's behalf, with explicit per-connector permission.
3. **Tool composition** — new trigger type `on_tool_completed`. Tool A's output becomes Tool B's input. Already works because every tool has a programmatic interface.
4. **Cross-app observation** — extend beyond browser via OS-level accessibility APIs. Capture transformations done in Excel, Figma, Notion desktop. Same tool generation pipeline.
5. **Opt-in tool sharing** — anonymized template library. Teammates adopt each other's logic; each worker's own Mem0 layer re-personalizes the UI and conventions. Transforms the product from personal to team-multiplicative.
6. **Continuous re-generation** — as the worker's style drifts (new tag conventions, updated templates), the agent regenerates the tool. Version history in the registry lets them roll back.
7. **Tool marketplace (later)** — eventually, aggregated anonymized templates can bootstrap new workers faster. This is a business-model conversation, not a tech one.

---

## Appendix A — Repository Layout

```
/extension              # Team A (Plasmo + React + rrweb)
  /src
    /background         # event batcher, API client
    /content            # rrweb + clipboard capture + popup injection
    /popup              # extension icon popup — library view
  /manifest.json        # MV3, clipboard + activeTab + scripting perms

/backend                # Team B (FastAPI)
  /app
    /routes
      /v1               # §12.1 public endpoints
      /internal         # §12.3, §12.4 internal endpoints
    /registry           # Tool CRUD
    /artifacts          # blob storage
    /triggers           # pluggable evaluator
      url_visit.py      # v1
      schedule.py       # v2 stub
      email.py          # v2 stub
    /orchestrator       # Tool Orchestrator (§6.3)
    /scheduler          # detection loop
    /store              # SQLite models
  /tests

/ai                     # Team C (Python, OpenAI-compat K2-V2 client)
  /prompts
    detect.py
    generate.py
  /fixtures             # ← unblocks parallel work
    domain_a_events.json
    domain_a_detection.json
    domain_a_tool.json
    (repeat for b, c)
  /mem0_wrapper
  /primitive_registry   # whitelisted CDN libs
  /tests

/runtime                # Team D (JS primitives + tool shell)
  /primitives
    csv.js              # wrapper around papaparse with our conventions
    xlsx.js             # wrapper around sheetjs
    templating.js       # mustache + luxon helpers
  /shell
    tool_template.html  # skeleton the generator fills in
  /cdn.json             # whitelisted CDN URLs for generation prompt

/fixtures               # Team D (demo data)
  /domain_a_leads
    sample_leads.csv
    expected_output.xlsx
  /domain_b_tickers
    sample_tickers.txt
    sample_data.json
  /domain_c_tickets
    sample_ticket.json
    sample_customer.json

/docs
  SPEC.md               # this file
  DEMO_SCRIPT.md        # word-for-word demo walk-through
  CONTRACTS_CHANGELOG.md  # every change to §11 / §12, dated
```

---

## Appendix B — Sample Generated Tool (abbreviated HTML)

This is what a generated tool looks like. Included so Team D can validate the shape and so Team C can calibrate the generation prompt.

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<title>Lead List Formatter — Bob</title>
<script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
  :root { --bg:#0d1117; --fg:#c9d1d9; --accent:#58a6ff; --border:#30363d; }
  html,body { background:var(--bg); color:var(--fg); font:14px/1.5 -apple-system,sans-serif; margin:0; }
  .container { max-width:640px; margin:48px auto; padding:24px; }
  .drop-zone { border:2px dashed var(--border); padding:48px; text-align:center; border-radius:8px; cursor:pointer; }
  .drop-zone:hover { border-color:var(--accent); }
  .preview { margin-top:24px; padding:16px; border:1px solid var(--border); border-radius:8px; max-height:300px; overflow:auto; }
  button { background:var(--accent); color:var(--bg); border:none; padding:12px 24px; border-radius:6px; font-weight:600; cursor:pointer; }
</style>
</head>
<body>
<div class="container">
  <h1>Format My Leads</h1>
  <p>Drop your raw lead CSV — get a filtered, tagged XLSX for CRM import.</p>

  <div id="drop" class="drop-zone">Drop CSV here, click to pick, or paste below</div>
  <textarea id="paste" placeholder="…or paste CSV text here" style="width:100%;height:80px;margin-top:12px;background:var(--bg);color:var(--fg);border:1px solid var(--border);padding:8px;"></textarea>

  <div id="preview" class="preview" hidden></div>
  <button id="download" hidden>Download XLSX</button>

  <div id="feedback" style="margin-top:48px;font-size:12px;opacity:0.6;">
    <span>How did I do? </span>
    <button onclick="sendFeedback('good')">Works well</button>
    <button onclick="sendFeedback('bad')">Something's off</button>
  </div>
</div>

<script>
// ──────────────────────────────────────────────────────────────
//  window.Tool — pure function interface (REQUIRED for agent-ready)
// ──────────────────────────────────────────────────────────────
window.Tool = {
  metadata: {
    id: "tool_lead_formatter_v1",
    name: "Lead List Formatter",
    version: "1.0",
    input_type: "csv_string",
    output_type: "xlsx_blob"
  },

  defaultConfig: {
    tag_pattern: "[Q2-Outbound-Fintech-BK]",
    filter_min_stage: "series_b",
    filter_industry: "fintech",
    sort_by: "employees_desc"
  },

  async transform(input, config = {}) {
    const cfg = { ...this.defaultConfig, ...config };
    const parsed = Papa.parse(input.trim(), { header: true, skipEmptyLines: true });
    if (parsed.errors.length) throw new Error("Bad CSV: " + parsed.errors[0].message);

    // Bob's specific logic:
    const stageOrder = { "seed": 0, "series_a": 1, "series_b": 2, "series_c": 3, "series_d": 4 };
    const minStage = stageOrder[cfg.filter_min_stage];

    const filtered = parsed.data
      .filter(r => (r.Industry || "").toLowerCase() === cfg.filter_industry)
      .filter(r => stageOrder[(r.Stage || "").toLowerCase().replace(" ", "_")] >= minStage)
      .sort((a,b) => Number(b.Employees || 0) - Number(a.Employees || 0))
      .map(r => ({ ...r, Tag: cfg.tag_pattern }));

    const ws = XLSX.utils.json_to_sheet(filtered);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Leads");
    const buf = XLSX.write(wb, { type: "array", bookType: "xlsx" });
    return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }
};

// ──────────────────────────────────────────────────────────────
//  UI — calls window.Tool.transform(). Do not duplicate logic here.
// ──────────────────────────────────────────────────────────────
let lastOutput = null;

async function run(csvText) {
  try {
    const blob = await window.Tool.transform(csvText);
    lastOutput = blob;
    document.getElementById("preview").hidden = false;
    document.getElementById("preview").textContent = "Preview: " + blob.size + " bytes of XLSX ready.";
    document.getElementById("download").hidden = false;
  } catch (e) {
    document.getElementById("preview").hidden = false;
    document.getElementById("preview").textContent = "Error: " + e.message;
  }
}

document.getElementById("drop").addEventListener("click", () => {
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".csv";
  inp.onchange = async e => run(await e.target.files[0].text());
  inp.click();
});
document.getElementById("drop").addEventListener("drop", async e => {
  e.preventDefault();
  run(await e.dataTransfer.files[0].text());
});
document.getElementById("drop").addEventListener("dragover", e => e.preventDefault());
document.getElementById("paste").addEventListener("input", e => {
  if (e.target.value.length > 20) run(e.target.value);
});
document.getElementById("download").addEventListener("click", () => {
  const url = URL.createObjectURL(lastOutput);
  const a = document.createElement("a");
  a.href = url;
  a.download = `leads_${new Date().toISOString().slice(0,10)}.xlsx`;
  a.click();
});

function sendFeedback(kind) {
  // POST to backend /v1/feedback. Omitted here.
}
</script>
</body>
</html>
```

Note how the transformation logic lives entirely inside `window.Tool.transform()` — the UI just calls it. A future proactive agent loads this HTML headlessly, ignores the UI, and calls `window.Tool.transform(csvData)` directly. **Same artifact, two consumers.**

---

## Appendix C — Contracts One-Liner

If you're on the team at 2am reading this to remember what you agreed to:
- You talk to other teams only through §12 endpoints using §11 schemas.
- You do not import anyone else's code.
- If you need to change §11 or §12, you update `/docs/CONTRACTS_CHANGELOG.md` and Slack the whole team before writing code.

---

## Appendix D — Agent-Later Quick Reference

If you're about to make a v1 design decision, check: would this block v2's proactive agent?

- [ ] Is your change visible only through §12? (Good — won't block.)
- [ ] Are you adding logic that depends on human-driven UI interaction? (Bad — put it in `window.Tool.transform()` instead, so the agent can call it.)
- [ ] Are you hardcoding a trigger type check? (Bad — go through the Trigger Evaluator.)
- [ ] Are you skipping `stats` updates on tool runs? (Bad — v2 needs this history to predict invocations.)
- [ ] Are you making the Orchestrator stub assume an HTTP request context? (Bad — v2 calls it from the scheduler, not HTTP.)

When in doubt: design for "a program is calling this," not "a human is calling this."

---

*End of spec v1.0.*

# Vim Diesel

Vim Diesel is a personal workflow agent that watches how someone completes a repeated task in the browser and quietly turns that behavior into a small reusable tool.

The core idea comes directly from `SPEC.md`:
- It is not browser automation.
- It is not a chatbot.
- It is a personal tool factory that captures how a worker thinks, then rebuilds that workflow as a self-contained tool.

In the current demo, Bob exports a CSV, cleans it up in Excel, and the system learns that pattern. On the next day, Vim offers to generate a tool for the same workflow, then later updates that tool when a reviewer email changes the formula.

## What This Repo Contains

- `extension/`
  Chrome extension built with Plasmo. Handles capture, page suggestions, popup UI, and showcase launching.
- `backend/`
  FastAPI app for demo state, tool APIs, storage, artifact serving, and orchestration stubs.
- `ai/`
  AI-side prompt logic, model clients, heuristics, and showcase summarization/update planning.
- `runtime/`
  Shared primitives for generated tools.
- `fixtures/`
  Mock sites, seeded tools, sample artifacts, and demo data.
- `demo/`
  Mirrored standalone demo copies of the main showcase page.
- `SPEC.md`
  Product, architecture, and build spec that defines the system direction.

## Setup

### 1. Backend

Run the backend on port `8000`:

```bash
python3 -m uvicorn backend.app.main:app --reload --port 8000
```

### 2. Mock Sites

Serve the mock sites on port `8012`:

```bash
python3 -m http.server 8012 --directory fixtures/mock_sites
```

Main demo URL:

```text
http://127.0.0.1:8012/portal.example.com/leads/
```

### 3. Extension

Install dependencies and build the extension:

```bash
cd extension
npm install
npm run build
```

### 4. Launch The Showcase

From `extension/`:

```bash
npm run showcase:launch
```

This launches the showcase browser flow and opens the main demo page.

## Demo Files

- Root served showcase:
  `fixtures/mock_sites/portal.example.com/leads/index.html`
- Mirrored copies:
  `demo/demo.html`
  `demo/demo2.html`

## Architecture

At a high level, the system has four layers:

### 1. Browser Extension

The extension captures signals from the worker's repeated actions:
- clicks
- inputs
- downloads
- navigation context

It also decides when to surface a helper/tool suggestion on the current page.

### 2. Backend Core

The backend stores observed events and tool state, serves tool artifacts, and drives the showcase demo state machine. In the demo flow it is also responsible for:
- advancing the “next day” story
- storing graph state
- tracking workbook/tool/email state
- serving downloadable CSV/XLSX artifacts

### 3. AI Layer

The AI layer detects patterns and plans updates to tools. For the showcase flow, it mainly helps with:
- summarizing the current workflow state
- converting email/change requests into structured formula updates
- falling back to deterministic heuristics when live model behavior is unavailable

### 4. Tool Runtime

Generated tools are designed as self-contained HTML artifacts with embedded JS behavior. The long-term architectural goal is that the same tool can be used:
- by a human through UI
- by a future agent through a programmatic interface

## Current Showcase Flow

1. Bob exports a shortlist CSV from the deal portal.
2. Bob cleans the workbook in Excel.
3. The graph records the workflow and formula context.
4. On the next day, Vim offers to generate a tool from that repeated behavior.
5. The tool can re-run the CSV-to-Excel transformation.
6. An Outlook email can request a formula update.
7. Vim updates the tool and records that change in the workflow graph.

## Useful References

- `SPEC.md`
- `docs/CONTRACTS.md`
- `backend/README.md`
- `extension/README.md`
- `demo/README.md`

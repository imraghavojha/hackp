# AI Lane

AI owns:
- detection prompt
- generation prompt
- model client
- Mem0 preference wrapper
- primitive whitelist
- fixture triplets

Start with Domain A and keep outputs aligned to `runtime/shell/tool_template.html`.

Run locally:
- `python3 -m uvicorn ai.app:app --reload --port 8001`

Current behavior:
- detects repeated lead-export work for Domain A
- generates a browser-runnable HTML artifact with `window.Tool.transform()`

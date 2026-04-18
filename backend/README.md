# Platform Lane

Backend owns:
- event intake
- tool lookup
- artifact serving
- feedback logging
- trigger evaluation
- detection loop
- orchestrator stub

First milestone:
- serve stable fixture responses for the extension

Run locally:
- `python3 -m uvicorn backend.app.main:app --reload --port 8000`
- `PWA_AI_BASE_URL=http://127.0.0.1:8001 python3 -m uvicorn backend.app.main:app --reload --port 8000`

Notes:
- the backend persists local state under `backend/data/`
- the AI service is expected on `http://127.0.0.1:8001` by default

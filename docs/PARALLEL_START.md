# Parallel Start

## Person A: Extension

Own:
- `extension/**`

First moves:
- Wire event capture with privacy filters
- Batch to `POST /v1/events`
- Stub popup + launcher against fixture responses
- Keep the extension popup as a small library view only

Do not touch:
- `backend/**`
- `ai/**`
- `runtime/**`
- `fixtures/**`

## Person B: Platform

Own:
- `backend/**`
- `ai/**`
- `runtime/**`
- `fixtures/**`

First moves:
- Stub the public endpoints so the extension can integrate immediately
- Serve one hand-authored HTML artifact before live AI
- Lock the runtime contract and Domain A fixtures
- Add the detection/generation loop after the artifact path works

Do not touch:
- `extension/**`

## Shared files

Coordinate before changing:
- `SPEC.md`
- `docs/CONTRACTS.md`
- `docs/CONTRACTS_CHANGELOG.md`

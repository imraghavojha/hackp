# Shared Contracts

Use `SPEC.md` as source of truth. This file is the short freeze line for parallel work.

## Event shape

Required fields:
- `session_id`
- `user_id`
- `timestamp`
- `url`
- `event_type`
- `target`
- `value`
- `metadata`

Allowed `event_type` values:
- `click`
- `input`
- `navigation`
- `copy`
- `paste`
- `submit`
- `select`
- `file_download`

## Extension -> Backend

- `POST /v1/events` -> `{"accepted": number, "buffered": number}`
- `GET /v1/tools/for_url?url=...&user_id=...` -> `{"tools": [...]}`
- `GET /v1/tools/{id}/artifact` -> HTML artifact
- `POST /v1/tools/{id}/usage` -> `{"logged": true}`
- `POST /v1/feedback` -> `{"stored": true, "memory_id": "..."}`

## Backend -> AI

- `POST /ai/detect_transformation` -> detection JSON or `{"detected": false}`
- `POST /ai/generate_tool` -> tool record + `html_artifact`

## Generated tool runtime

Every generated artifact must expose:

```js
window.Tool = {
  metadata: { id, name, version, input_type, output_type },
  async transform(input, config = {}) {},
  defaultConfig: {}
}
```

Change rule:
- If you change a field or endpoint here, update `docs/CONTRACTS_CHANGELOG.md` in the same diff.

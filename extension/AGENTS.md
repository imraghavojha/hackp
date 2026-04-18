# Extension AI Rules

- Touch only `extension/**` unless the human explicitly wants a contract change.
- Read `docs/CONTRACTS.md` before changing request or response shapes.
- Do not edit `backend/`, `ai/`, `runtime/`, or `fixtures/`.
- If a shared contract changes, update `docs/CONTRACTS.md` and `docs/CONTRACTS_CHANGELOG.md` together.
- Prefer stubs and mocks over blocking on another lane.

# Platform AI Rules

- Touch `backend/**`, `ai/**`, `runtime/**`, and `fixtures/**` only.
- Do not edit `extension/**`.
- Keep request and response shapes aligned with `docs/CONTRACTS.md`.
- If a shared contract changes, update `docs/CONTRACTS.md` and `docs/CONTRACTS_CHANGELOG.md` together.
- Prefer fixture-backed stubs that unblock the extension lane early.

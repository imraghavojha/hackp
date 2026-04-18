# Mock Sites

Serve these locally for browser testing:

```bash
python3 -m http.server 8012 --directory fixtures/mock_sites
```

Then open:
- `http://127.0.0.1:8012/portal.example.com/leads/`
- `http://127.0.0.1:8012/research.example.com/tickers/`
- `http://127.0.0.1:8012/support.example.com/tickets/`

Each URL intentionally contains the domain-pattern substring the extension trigger evaluator is already looking for.

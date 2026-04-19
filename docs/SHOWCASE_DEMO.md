# Showcase Demo

Main demo page:
- `http://127.0.0.1:8012/portal.example.com/leads/`
- mirrored standalone file: `/Users/kuldeepojha/Desktop/hackp-showcase/demo.html`

Reset the whole demo:
- `POST http://127.0.0.1:8000/demo/showcase/reset`

Main flow:
1. Export CSV in the Research tab.
2. Rename both headers and add both formulas in the Excel tab.
3. Save as XLSX.
4. Advance to the next day.
5. Review the helper and apply Bob's change.
6. Open the Inbox tab and inject a sample email or sync Gmail.
7. Return to Tool Manager and apply the analyst update.
8. Click the extension badge to show the calm update/help message.

Optional live Gmail sync:
- Set `PWA_DEMO_GMAIL_CREDENTIALS_PATH`
- Set `PWA_DEMO_GMAIL_TOKEN_PATH`
- Optional filter: `PWA_DEMO_GMAIL_QUERY`
- Then call `POST /demo/showcase/inbox/sync-gmail`

Notes:
- The extension suggestion works best on the served portal URL, not the standalone file URL.
- `file://` can still load the page, but Chrome may require enabling extension access to file URLs if you want the real extension there.

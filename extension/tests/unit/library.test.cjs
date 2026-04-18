const test = require("node:test")
const assert = require("node:assert/strict")

const { upsertLibraryTools, updateLibraryTool, sortLibraryTools } = require("../../.test-dist/lib/library.js")
const { parseArtifactToolId, isArtifactPage } = require("../../.test-dist/lib/tool-pages.js")
const { backoffDelayMs } = require("../../.test-dist/background/retry.js")

function makeTool(id, overrides = {}) {
  return {
    id,
    user_id: "bob",
    name: `Tool ${id}`,
    description: "demo",
    created_at: "2026-04-18T09:00:00Z",
    trigger: {
      type: "on_url_visit",
      url_pattern: "portal.example.com",
      prompt: "open"
    },
    ui_prefs: {
      theme: "light",
      density: "comfortable"
    },
    transformation_summary: [],
    status: "ready",
    stats: {
      times_used: 0,
      last_used: null,
      avg_duration_ms: null
    },
    artifact: {
      artifact_id: `art_${id}`
    },
    ...overrides
  }
}

test("library tools are merged, updated, and sorted newest-first", () => {
  const first = upsertLibraryTools([], [makeTool("tool_a")], "https://portal.example.com", "2026-04-18T10:00:00Z")
  const withSecond = upsertLibraryTools(first, [makeTool("tool_b")], "https://portal.example.com", "2026-04-18T11:00:00Z")
  const updated = updateLibraryTool(withSecond, "tool_a", {
    last_opened_at: "2026-04-18T12:00:00Z"
  })

  const sorted = sortLibraryTools(updated)
  assert.equal(sorted[0].id, "tool_a")
  assert.equal(sorted[1].id, "tool_b")
})

test("tool page parsing and retry backoff are stable", () => {
  assert.equal(parseArtifactToolId("http://127.0.0.1:8000/v1/tools/tool_x/artifact"), "tool_x")
  assert.equal(parseArtifactToolId("http://127.0.0.1:8000/not-a-tool"), null)
  assert.equal(isArtifactPage("http://127.0.0.1:8000/v1/tools/tool_x/artifact"), true)
  assert.equal(isArtifactPage("https://portal.example.com/leads"), false)
  assert.deepEqual([backoffDelayMs(0), backoffDelayMs(1), backoffDelayMs(2)], [250, 500, 1000])
})

const test = require("node:test")
const assert = require("node:assert/strict")

const { isDeniedUrl, shouldCaptureField, redactValue } = require("../../.test-dist/content/privacy.js")
const { buildObservedEvent } = require("../../.test-dist/content/capture.js")

test("privacy helpers block denied URLs and sensitive fields", () => {
  assert.equal(isDeniedUrl("https://bank.example.com/dashboard", ["custom.example"]), true)
  assert.equal(isDeniedUrl("https://work.example.com", ["custom.example"]), false)
  assert.equal(shouldCaptureField("password", null, "secret"), false)
  assert.equal(shouldCaptureField("text", "cc-number", "4111 1111 1111 1111"), false)
  assert.equal(shouldCaptureField("text", "email", "hello@example.com"), true)
})

test("captured values are truncated and custom denylist is respected", () => {
  const observed = buildObservedEvent(
    {
      session_id: "sess_1",
      user_id: "bob",
      timestamp: "2026-04-18T09:00:00Z",
      url: "https://portal.example.com/leads",
      event_type: "copy",
      target: { tag: "td", role: null, text: "Acme", aria_label: null },
      metadata: {},
      extra_denylist: ["medical.example.com"]
    },
    "A".repeat(6_000)
  )

  assert.ok(observed)
  assert.equal(observed.value.length, 5_000)

  const denied = buildObservedEvent(
    {
      session_id: "sess_1",
      user_id: "bob",
      timestamp: "2026-04-18T09:00:00Z",
      url: "https://medical.example.com/patient",
      event_type: "copy",
      target: { tag: "td", role: null, text: "Acme", aria_label: null },
      metadata: {},
      extra_denylist: ["medical.example.com"]
    },
    "secret"
  )

  assert.equal(denied, null)
  assert.equal(redactValue("B".repeat(6_000)).length, 5_000)
})

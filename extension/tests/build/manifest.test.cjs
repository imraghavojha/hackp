const test = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")

const manifestPath = path.join(__dirname, "..", "..", "build", "chrome-mv3-prod", "manifest.json")

test("built manifest includes popup, background, and content script entries", () => {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"))

  assert.equal(manifest.name, "Personal Workflow Agent")
  assert.equal(typeof manifest.background?.service_worker, "string")
  assert.equal(manifest.action?.default_popup, "popup.html")
  assert.ok(Array.isArray(manifest.content_scripts))
  assert.ok(manifest.content_scripts.length > 0)
  assert.deepEqual(manifest.content_scripts[0].matches, ["<all_urls>"])
})

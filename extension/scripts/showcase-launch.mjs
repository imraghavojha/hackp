import os from "node:os"
import path from "node:path"
import { mkdtemp } from "node:fs/promises"
import { existsSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { chromium } from "playwright"

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const extensionRoot = path.resolve(scriptDir, "..")
const extensionPath = path.join(extensionRoot, "build", "chrome-mv3-prod")

async function ensure(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Expected ${url} to be available, got ${response.status}`)
  }
}

async function main() {
  if (!existsSync(extensionPath) || !existsSync(path.join(extensionPath, "manifest.json"))) {
    throw new Error(`Built extension not found at ${extensionPath}. Run 'npm run build' first.`)
  }

  await ensure("http://127.0.0.1:8000/health")
  await ensure("http://127.0.0.1:8001/health")
  await ensure("http://127.0.0.1:8012/portal.example.com/leads/")

  await fetch("http://127.0.0.1:8000/demo/showcase/reset", { method: "POST" })

  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "hackp-showcase-browser-"))
  const headless = process.argv.includes("--headless")

  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: "chromium",
    headless,
    viewport: { width: 1520, height: 980 },
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`
    ]
  })

  const page = context.pages()[0] ?? await context.newPage()
  await page.goto("http://127.0.0.1:8012/portal.example.com/leads/", { waitUntil: "domcontentloaded" })

  console.log("Showcase browser launched.")
  console.log("Profile:", userDataDir)
  console.log("URL:", page.url())
  console.log("This Chromium profile only has the demo extension loaded.")

  if (headless) {
    await context.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})

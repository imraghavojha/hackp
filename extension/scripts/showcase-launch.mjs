import path from "node:path"
import os from "node:os"
import { existsSync, mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { spawn } from "node:child_process"

import { chromium } from "playwright"

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const extensionRoot = path.resolve(scriptDir, "..")
const repoRoot = path.resolve(extensionRoot, "..")
const extensionPath = path.join(extensionRoot, "build", "chrome-mv3-prod")
const backgroundChildren = []

async function ensure(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Expected ${url} to be available, got ${response.status}`)
  }
}

async function isHealthy(url) {
  try {
    await ensure(url)
    return true
  } catch {
    return false
  }
}

function startProcess(command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    stdio: "ignore",
    detached: false
  })
  backgroundChildren.push(child)
  return child
}

async function waitForUrl(url, timeoutMs = 15000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await isHealthy(url)) {
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

async function ensureDemoServices() {
  if (!(await isHealthy("http://127.0.0.1:8000/health"))) {
    startProcess("python3", ["-m", "uvicorn", "backend.app.main:app", "--port", "8000"], repoRoot)
    await waitForUrl("http://127.0.0.1:8000/health")
  }

  if (!(await isHealthy("http://127.0.0.1:8012/portal.example.com/leads/"))) {
    startProcess("python3", ["-m", "http.server", "8012", "--directory", "fixtures/mock_sites"], repoRoot)
    await waitForUrl("http://127.0.0.1:8012/portal.example.com/leads/")
  }
}

async function main() {
  if (!existsSync(extensionPath) || !existsSync(path.join(extensionPath, "manifest.json"))) {
    throw new Error(`Built extension not found at ${extensionPath}. Run 'npm run build' first.`)
  }

  await ensureDemoServices()

  await fetch("http://127.0.0.1:8000/demo/showcase/reset", { method: "POST" })

  const userDataDir = path.join(os.homedir(), ".hackp-showcase-browser")
  const downloadsDir = path.join(os.homedir(), "Downloads")
  mkdirSync(userDataDir, { recursive: true })
  mkdirSync(downloadsDir, { recursive: true })
  const headless = process.argv.includes("--headless")

  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: "chromium",
    headless,
    viewport: { width: 1520, height: 980 },
    acceptDownloads: true,
    downloadsPath: downloadsDir,
    args: [
      "--no-first-run",
      "--no-default-browser-check",
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`
    ]
  })

  const page = context.pages()[0] ?? await context.newPage()
  await page.goto("http://127.0.0.1:8012/portal.example.com/leads/", { waitUntil: "domcontentloaded" })

  console.log("Showcase browser launched.")
  console.log("Profile:", userDataDir)
  console.log("Downloads:", downloadsDir)
  console.log("URL:", page.url())
  console.log("This Chromium profile only has the demo extension loaded.")

  if (headless) {
    await context.close()
  }
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    for (const child of backgroundChildren) {
      child.kill(signal)
    }
    process.exit(0)
  })
}

main().catch((error) => {
  console.error(error)
  for (const child of backgroundChildren) {
    child.kill("SIGTERM")
  }
  process.exit(1)
})

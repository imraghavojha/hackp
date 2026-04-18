import { backendApi } from "../background/api"
import { sendExtensionMessage } from "../lib/messaging"
import type { ToolRecord } from "../types/tools"

const OVERLAY_ROOT_ID = "pwa-inline-helper-root"

function ensureOverlayStyles() {
  if (document.getElementById("pwa-inline-helper-styles")) {
    return
  }

  const style = document.createElement("style")
  style.id = "pwa-inline-helper-styles"
  style.textContent = `
    #${OVERLAY_ROOT_ID} {
      position: fixed;
      inset: 0;
      z-index: 2147483647;
      display: grid;
      place-items: center;
      background: rgba(15, 23, 42, 0.18);
      backdrop-filter: blur(6px);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    .pwa-helper-card {
      width: min(720px, calc(100vw - 32px));
      height: min(82vh, 860px);
      background: #ffffff;
      color: #111827;
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-radius: 22px;
      box-shadow: 0 24px 64px rgba(15, 23, 42, 0.16);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .pwa-helper-header {
      padding: 16px 18px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: #f8fafc;
    }
    .pwa-helper-title {
      font-size: 1rem;
      font-weight: 700;
      margin: 0;
    }
    .pwa-helper-subtitle {
      font-size: 0.9rem;
      color: #6b7280;
      margin: 4px 0 0;
    }
    .pwa-helper-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .pwa-helper-actions button {
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .pwa-helper-actions .primary {
      background: #1d4ed8;
      color: #ffffff;
    }
    .pwa-helper-actions .secondary {
      background: #e5e7eb;
      color: #111827;
    }
    .pwa-helper-actions .ghost {
      background: transparent;
      color: #374151;
    }
    .pwa-helper-body {
      position: relative;
      background: #ffffff;
    }
    .pwa-helper-loader {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
    .pwa-helper-loader[data-hidden="true"] {
      display: none;
    }
    .pwa-helper-loader__stack {
      text-align: center;
      display: grid;
      gap: 14px;
      justify-items: center;
      padding: 24px;
    }
    .pwa-helper-loader__orb {
      width: 88px;
      height: 88px;
      border-radius: 999px;
      background: radial-gradient(circle at center, rgba(29, 78, 216, 0.28), rgba(29, 78, 216, 0.04) 60%, transparent 70%);
      position: relative;
      animation: pwa-orb-breathe 1.8s ease-in-out infinite;
    }
    .pwa-helper-loader__orb::before,
    .pwa-helper-loader__orb::after {
      content: "";
      position: absolute;
      inset: 12px;
      border: 1px solid rgba(29, 78, 216, 0.28);
      border-radius: 999px;
      animation: pwa-ring-pulse 2.2s ease-out infinite;
    }
    .pwa-helper-loader__orb::after {
      inset: 0;
      animation-delay: 0.4s;
    }
    .pwa-helper-loader__title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #111827;
    }
    .pwa-helper-loader__text {
      color: #6b7280;
      max-width: 420px;
      line-height: 1.45;
    }
    .pwa-helper-frame {
      border: 0;
      width: 100%;
      height: 100%;
      background: #ffffff;
    }
    @keyframes pwa-orb-breathe {
      0%, 100% { transform: scale(0.96); opacity: 0.88; }
      50% { transform: scale(1.04); opacity: 1; }
    }
    @keyframes pwa-ring-pulse {
      0% { transform: scale(0.9); opacity: 0.7; }
      100% { transform: scale(1.25); opacity: 0; }
    }
  `
  document.documentElement.appendChild(style)
}

export interface HelperOverlayHandle {
  dispose: () => void
}

async function wait(ms: number) {
  await new Promise((resolve) => globalThis.setTimeout(resolve, ms))
}

export async function showInlineHelper(tool: ToolRecord): Promise<HelperOverlayHandle> {
  ensureOverlayStyles()

  document.getElementById(OVERLAY_ROOT_ID)?.remove()
  const root = document.createElement("div")
  root.id = OVERLAY_ROOT_ID
  root.dataset.extensionOwned = "true"
  root.innerHTML = `
    <section class="pwa-helper-card">
      <header class="pwa-helper-header">
        <div>
          <div class="pwa-helper-title">${tool.name}</div>
          <div class="pwa-helper-subtitle">${tool.trigger.prompt}</div>
        </div>
        <div class="pwa-helper-actions">
          <button class="primary" data-action="popout">Open in separate window</button>
          <button class="ghost" data-action="close">Close</button>
        </div>
      </header>
      <div class="pwa-helper-body">
        <div class="pwa-helper-loader" data-hidden="false">
          <div class="pwa-helper-loader__stack">
            <div class="pwa-helper-loader__orb"></div>
            <div class="pwa-helper-loader__title">Preparing your helper</div>
            <div class="pwa-helper-loader__text" data-loading-text>
              Reviewing the repeated workflow and loading the helper in place.
            </div>
          </div>
        </div>
        <iframe class="pwa-helper-frame" title="${tool.name} helper"></iframe>
      </div>
    </section>
  `

  const iframe = root.querySelector<HTMLIFrameElement>("iframe")
  const loader = root.querySelector<HTMLElement>(".pwa-helper-loader")
  const loadingText = root.querySelector<HTMLElement>("[data-loading-text]")

  const dispose = () => root.remove()

  root.addEventListener("click", (event) => {
    const target = event.target
    if (!(target instanceof HTMLElement)) {
      return
    }

    const action = target.dataset.action
    if (action === "close") {
      dispose()
    }
    if (action === "popout") {
      void sendExtensionMessage({ type: "extension/open-tool", toolId: tool.id })
    }
  })

  document.documentElement.appendChild(root)

  if (!iframe || !loader || !loadingText) {
    return { dispose }
  }

  const artifactUrl = backendApi.getArtifactUrl(tool.id)
  loadingText.textContent = "Reviewing the workflow and preparing the helper surface."
  await wait(850)
  loadingText.textContent = "Loading the helper interface for this task."

  const frameLoaded = new Promise<void>((resolve) => {
    iframe.addEventListener("load", () => resolve(), { once: true })
  })

  iframe.src = artifactUrl

  await Promise.race([frameLoaded, wait(5_000)])
  loader.dataset.hidden = "true"

  return { dispose }
}

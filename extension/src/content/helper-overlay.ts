import { backendApi } from "../background/api"
import { sendExtensionMessage } from "../lib/messaging"
import type { AnalysisRecord, ToolRecord } from "../types/tools"

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
      top: 18px;
      right: 18px;
      bottom: 18px;
      width: min(520px, calc(100vw - 28px));
      z-index: 2147483647;
      display: block;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    .pwa-helper-card {
      width: 100%;
      height: 100%;
      background: #ffffff;
      color: #111827;
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-radius: 22px;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .pwa-helper-header {
      padding: 18px 20px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
    }
    .pwa-helper-title {
      font-size: 1.08rem;
      font-weight: 700;
      margin: 0;
    }
    .pwa-helper-subtitle {
      font-size: 0.9rem;
      color: #667085;
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
      padding: 13px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      font-size: 0.95rem;
    }
    .pwa-helper-actions .primary {
      background: #1d4ed8;
      color: #ffffff;
    }
    .pwa-helper-actions .secondary {
      background: #f5f7fb;
      color: #111827;
    }
    .pwa-helper-actions .ghost {
      background: transparent;
      color: #667085;
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
      background: linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
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
      color: #667085;
      max-width: 420px;
      line-height: 1.45;
    }
    .pwa-helper-frame {
      border: 0;
      width: 100%;
      height: 100%;
      background: #ffffff;
    }
    .pwa-helper-shell {
      position: relative;
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      transition: grid-template-columns 180ms ease;
    }
    .pwa-helper-shell[data-drawer-open="true"] {
      grid-template-columns: minmax(0, 1fr) 320px;
    }
    .pwa-helper-sidebar-toggle {
      position: absolute;
      top: 18px;
      right: 18px;
      z-index: 2;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: rgba(255, 255, 255, 0.96);
      color: #111827;
      font: inherit;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
    }
    .pwa-helper-sidebar {
      border-left: 1px solid rgba(148, 163, 184, 0.18);
      background: #f8fbff;
      color: #111827;
      padding: 18px;
      display: none;
      gap: 14px;
      align-content: start;
    }
    .pwa-helper-shell[data-drawer-open="true"] .pwa-helper-sidebar {
      display: grid;
    }
    .pwa-helper-sidebar div,
    .pwa-helper-sidebar p {
      color: #667085;
    }
    .pwa-helper-sidebar textarea {
      width: 100%;
      min-height: 132px;
      box-sizing: border-box;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.24);
      background: #ffffff;
      color: #111827;
      padding: 12px 14px;
      font: inherit;
      resize: vertical;
    }
    .pwa-helper-sidebar .save-button {
      border: 0;
      border-radius: 999px;
      padding: 13px 18px;
      background: #1d4ed8;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
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

export async function showInlineHelper(tool: ToolRecord, analysis: AnalysisRecord | null): Promise<HelperOverlayHandle> {
  ensureOverlayStyles()

  document.getElementById(OVERLAY_ROOT_ID)?.remove()
  const root = document.createElement("div")
  root.id = OVERLAY_ROOT_ID
  root.dataset.extensionOwned = "true"
  const whyText = analysis
    ? `${analysis.summary} Repetition count: ${analysis.repetition_count}. Confidence: ${analysis.confidence ?? "n/a"}.`
    : "This helper was suggested because the workflow looks similar to a repeated task."
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
              Reviewing your repeated workflow and preparing the helper in place.
            </div>
          </div>
        </div>
        <div class="pwa-helper-shell" data-drawer-open="false">
          <button class="pwa-helper-sidebar-toggle" data-action="toggle-drawer">Personalize</button>
          <iframe class="pwa-helper-frame" title="${tool.name} helper"></iframe>
          <aside class="pwa-helper-sidebar">
            <div>
              <strong style="display:block;margin-bottom:6px;">Why this helper?</strong>
              <div style="font-size:0.9rem;line-height:1.5;">${whyText}</div>
            </div>
            <div>
              <strong style="display:block;margin-bottom:6px;">Personalize it</strong>
              <div style="font-size:0.85rem;margin-bottom:8px;">Adjust the helper after reviewing the first result.</div>
              <textarea data-chat-input placeholder="Example: make the tone warmer, add a total row, use Q3 tags."></textarea>
              <button class="save-button" data-action="save-preference" style="margin-top:10px;">Save preference</button>
              <div data-chat-status style="margin-top:8px;font-size:0.84rem;">Saved preferences will affect future generations.</div>
            </div>
          </aside>
        </div>
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
    if (action === "toggle-drawer") {
      const shell = root.querySelector<HTMLElement>(".pwa-helper-shell")
      const toggle = root.querySelector<HTMLElement>(".pwa-helper-sidebar-toggle")
      const next = shell?.dataset.drawerOpen === "true" ? "false" : "true"
      if (shell) shell.dataset.drawerOpen = next
      if (toggle) toggle.textContent = next === "true" ? "Hide personalize" : "Personalize"
    }
    if (action === "save-preference") {
      const textarea = root.querySelector<HTMLTextAreaElement>("[data-chat-input]")
      const status = root.querySelector<HTMLElement>("[data-chat-status]")
      const feedback = textarea?.value.trim() ?? ""
      if (!feedback) {
        if (status) status.textContent = "Add a message first."
        return
      }
      void sendExtensionMessage({
        type: "extension/tool-feedback",
        payload: {
          toolId: tool.id,
          feedback,
          context: "chat",
          succeeded: true,
          durationMs: 1_000
        }
      }).then((response) => {
        if (status) status.textContent = response.ok ? "Preference saved. The next generated helper will use it." : "Couldn't save preference."
      })
    }
  })

  document.documentElement.appendChild(root)

  if (!iframe || !loader || !loadingText) {
    return { dispose }
  }

  const artifactUrl = backendApi.getArtifactUrl(tool.id)
  loadingText.textContent = "Reviewing the workflow and preparing the helper surface."
  await wait(1200)
  loadingText.textContent = "Brewing the helper interface for this task."
  await wait(1200)

  const frameLoaded = new Promise<void>((resolve) => {
    iframe.addEventListener("load", () => resolve(), { once: true })
  })

  iframe.src = artifactUrl

  await Promise.race([frameLoaded, wait(5_000)])
  loader.dataset.hidden = "true"

  return { dispose }
}

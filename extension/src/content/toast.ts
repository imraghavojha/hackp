import { POPUP_TTL_MS } from "../lib/constants"
import { sendExtensionMessage } from "../lib/messaging"
import type { AnalysisRecord, ToolRecord } from "../types/tools"

const TOAST_ROOT_ID = "pwa-extension-toast-root"

function ensureToastStyles() {
  if (document.getElementById("pwa-extension-toast-styles")) {
    return
  }

  const style = document.createElement("style")
  style.id = "pwa-extension-toast-styles"
  style.textContent = `
    #${TOAST_ROOT_ID} {
      position: fixed;
      right: 24px;
      bottom: 24px;
      width: 320px;
      z-index: 2147483647;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    .pwa-toast {
      border-radius: 18px;
      box-shadow: 0 14px 36px rgba(15, 23, 42, 0.12);
      border: 1px solid rgba(148, 163, 184, 0.24);
      overflow: hidden;
      transform: translateY(18px);
      opacity: 0;
      animation: pwa-slide-in 180ms ease-out forwards;
    }
    .pwa-toast[data-theme="dark"] {
      background: #111827;
      color: #f3f4f6;
    }
    .pwa-toast__inner {
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .pwa-toast__top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }
    .pwa-toast__title {
      font-weight: 700;
      font-size: 0.95rem;
    }
    .pwa-toast__prompt {
      font-size: 0.92rem;
      line-height: 1.45;
      color: inherit;
      opacity: 0.72;
    }
    .pwa-toast__controls {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pwa-toast__button {
      border: 0;
      border-radius: 999px;
      padding: 13px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      font-size: 0.95rem;
    }
    .pwa-toast__button--primary {
      background: #1d4ed8;
      color: #ffffff;
    }
    .pwa-toast__button--secondary {
      background: transparent;
      color: inherit;
      border: 1px solid rgba(148, 163, 184, 0.24);
    }
    .pwa-toast__ghost {
      border: 0;
      background: transparent;
      color: inherit;
      cursor: pointer;
      padding: 0;
      font-size: 1rem;
    }
    .pwa-toast__menu {
      display: none;
      gap: 8px;
      font-size: 0.85rem;
    }
    .pwa-toast__menu[data-open="true"] {
      display: flex;
    }
    @keyframes pwa-slide-in {
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }
  `
  document.documentElement.appendChild(style)
}

export interface ToastHandle {
  dispose: () => void
}

export function showSuggestionToast(
  tool: ToolRecord,
  origin: string,
  analysis: AnalysisRecord | null,
  onOpen: () => void
): ToastHandle {
  ensureToastStyles()

  const existing = document.getElementById(TOAST_ROOT_ID)
  existing?.remove()

  const root = document.createElement("div")
  root.id = TOAST_ROOT_ID
  root.dataset.extensionOwned = "true"
  const isShowcaseWorkflow = tool.trigger.url_pattern.includes("portal.example.com/leads")
  const prompt =
    analysis && isShowcaseWorkflow && analysis.repetition_count >= 1
      ? `I’ve seen this sequence before. Want me to turn it into a workflow?`
      : analysis && analysis.repetition_count >= 3
      ? `This is at least the third time I've seen you do this. Want me to make a helper for it?`
      : tool.trigger.prompt
  root.innerHTML = `
    <aside class="pwa-toast" data-theme="dark">
      <div class="pwa-toast__inner">
        <div class="pwa-toast__top">
          <div>
            <div class="pwa-toast__title">${tool.name}</div>
            <div class="pwa-toast__prompt">${prompt}</div>
          </div>
          <button class="pwa-toast__ghost" data-action="dismiss" aria-label="Dismiss">×</button>
        </div>
        <div class="pwa-toast__controls">
          <button class="pwa-toast__button pwa-toast__button--primary" data-action="open">${isShowcaseWorkflow ? "Open workflow" : "Open helper"}</button>
          <button class="pwa-toast__button pwa-toast__button--secondary" data-action="not-now">Not now</button>
          <button class="pwa-toast__ghost" data-action="menu">Options</button>
        </div>
        <div class="pwa-toast__menu" data-open="false">
          <button class="pwa-toast__ghost" data-action="suppress">Don't suggest here again</button>
        </div>
      </div>
    </aside>
  `

  const dispose = () => root.remove()

  root.addEventListener("click", (event) => {
    const target = event.target
    if (!(target instanceof HTMLElement)) {
      return
    }

    const action = target.dataset.action
    if (!action) {
      return
    }

    if (action === "open") {
      onOpen()
      dispose()
      return
    }

    if (action === "menu") {
      const menu = root.querySelector<HTMLElement>(".pwa-toast__menu")
      menu?.setAttribute("data-open", menu.getAttribute("data-open") === "true" ? "false" : "true")
      return
    }

    if (action === "suppress") {
      void sendExtensionMessage({ type: "extension/suppress-origin", origin })
    }

    dispose()
  })

  document.documentElement.appendChild(root)
  const timeout = globalThis.setTimeout(dispose, POPUP_TTL_MS)

  return {
    dispose: () => {
      globalThis.clearTimeout(timeout)
      dispose()
    }
  }
}

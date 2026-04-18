import { sendExtensionMessage } from "../lib/messaging"
import { parseArtifactToolId } from "../lib/tool-pages"

const FEEDBACK_ROOT_ID = "pwa-tool-feedback-root"

function ensureFeedbackStyles() {
  if (document.getElementById("pwa-tool-feedback-style")) {
    return
  }

  const style = document.createElement("style")
  style.id = "pwa-tool-feedback-style"
  style.textContent = `
    #${FEEDBACK_ROOT_ID} {
      position: fixed;
      left: 24px;
      right: 24px;
      bottom: 20px;
      z-index: 2147483647;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    .pwa-feedback {
      background: rgba(255, 255, 255, 0.98);
      color: #111827;
      border: 1px solid rgba(148, 163, 184, 0.22);
      box-shadow: 0 14px 36px rgba(15, 23, 42, 0.12);
      border-radius: 18px;
      padding: 14px 16px;
      display: grid;
      gap: 10px;
    }
    .pwa-feedback__actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pwa-feedback button {
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .pwa-feedback__good {
      background: #1d4ed8;
      color: #ffffff;
    }
    .pwa-feedback__bad {
      background: #e5e7eb;
      color: #111827;
      border: 1px solid rgba(148, 163, 184, 0.24);
    }
    .pwa-feedback textarea {
      min-height: 64px;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.22);
      background: #f9fafb;
      color: inherit;
      padding: 10px 12px;
      font: inherit;
      resize: vertical;
    }
  `
  document.documentElement.appendChild(style)
}

export function mountArtifactFeedback(url: string): void {
  const toolId = parseArtifactToolId(url)
  if (!toolId || document.getElementById(FEEDBACK_ROOT_ID)) {
    return
  }

  ensureFeedbackStyles()
  const startedAt = Date.now()
  const root = document.createElement("div")
  root.id = FEEDBACK_ROOT_ID
  root.dataset.extensionOwned = "true"
  root.innerHTML = `
    <section class="pwa-feedback">
      <strong>How did I do?</strong>
      <div class="pwa-feedback__actions">
        <button class="pwa-feedback__good" data-success="true">Works well</button>
        <button class="pwa-feedback__bad" data-success="false">Something's off</button>
      </div>
      <textarea placeholder="Optional feedback: make it dark mode, tag should say Q3 not Q2, add a total row"></textarea>
    </section>
  `

  root.addEventListener("click", (event) => {
    const target = event.target
    if (!(target instanceof HTMLButtonElement)) {
      return
    }

    const textarea = root.querySelector("textarea")
    const feedback = textarea?.value ?? ""
    const succeeded = target.dataset.success === "true"

    void sendExtensionMessage({
      type: "extension/tool-feedback",
      payload: {
        toolId,
        feedback,
        context: "ui",
        succeeded,
        durationMs: Math.max(Date.now() - startedAt, 1_000)
      }
    })

    target.textContent = "Sent"
    target.disabled = true
  })

  document.documentElement.appendChild(root)
}

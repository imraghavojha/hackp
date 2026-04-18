import { buildObservedEvent, buildTarget } from "./capture"
import { mountArtifactFeedback } from "./feedback"
import { pickSuggestedTool } from "./index"
import { isDeniedUrl } from "./privacy"
import { startRrwebSession } from "./rrweb"
import { showSuggestionToast } from "./toast"
import { POPUP_DELAY_MS } from "../lib/constants"
import { sendExtensionMessage } from "../lib/messaging"
import { getExtensionSettings } from "../lib/storage"
import { isArtifactPage } from "../lib/tool-pages"
import type { ObservedEvent, ObservedTarget } from "../types/events"
import type { ToolRecord } from "../types/tools"

interface ObserverContext {
  denylist: string[]
  rrwebCount: () => number
  sessionId: string
  userId: string
  currentToast: { dispose: () => void } | null
}

function createSessionId(): string {
  const storageKey = "pwa_extension_session_id"
  const existing = sessionStorage.getItem(storageKey)
  if (existing) {
    return existing
  }

  const value = crypto.randomUUID()
  sessionStorage.setItem(storageKey, value)
  return value
}

function buildMetadata(context: ObserverContext, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    viewport: [window.innerWidth, window.innerHeight],
    page_title: document.title,
    scroll_y: window.scrollY,
    rrweb_event_count: context.rrwebCount(),
    ...extra
  }
}

async function queueObservedEvent(event: ObservedEvent) {
  await sendExtensionMessage({
    type: "extension/queue-events",
    events: [event]
  })
}

function inferInputValue(target: Element): string {
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
    return target.value
  }

  if (target instanceof HTMLElement && target.isContentEditable) {
    return target.innerText
  }

  return ""
}

function inferClickEventType(target: EventTarget | null): ObservedEvent["event_type"] {
  if (target instanceof HTMLAnchorElement && (target.hasAttribute("download") || /download|export/i.test(target.textContent ?? ""))) {
    return "file_download"
  }

  if (
    target instanceof HTMLButtonElement &&
    /download|export|csv|xlsx/i.test([target.textContent, target.getAttribute("aria-label")].filter(Boolean).join(" "))
  ) {
    return "file_download"
  }

  return "click"
}

async function recordNavigation(context: ObserverContext, reason: string) {
  const event = buildObservedEvent(
    {
      session_id: context.sessionId,
      user_id: context.userId,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      event_type: "navigation",
      target: {
        tag: "document",
        role: null,
        text: document.title,
        aria_label: null
      },
      metadata: buildMetadata(context, { reason })
    },
    window.location.href
  )

  if (event) {
    await queueObservedEvent(event)
  }

  const settings = await getExtensionSettings()
  if (isDeniedUrl(window.location.href, settings.denylist) || settings.suppressedOrigins.includes(window.location.origin)) {
    context.currentToast?.dispose()
    context.currentToast = null
    return
  }

  const response = await sendExtensionMessage({
    type: "extension/fetch-tools-for-url",
    url: window.location.href
  })

  if (!response.ok || !response.tools || response.tools.length === 0) {
    context.currentToast?.dispose()
    context.currentToast = null
    return
  }

  const tool = pickSuggestedTool(window.location.href, response.tools)
  if (!tool) {
    return
  }

  context.currentToast?.dispose()
  globalThis.setTimeout(() => {
    context.currentToast = showSuggestionToast(tool, window.location.origin)
  }, POPUP_DELAY_MS)
}

function observeHistory(onChange: (reason: string) => void) {
  const originalPushState = history.pushState.bind(history)
  const originalReplaceState = history.replaceState.bind(history)

  history.pushState = ((...args: Parameters<History["pushState"]>) => {
    originalPushState(...args)
    onChange("pushState")
  }) as History["pushState"]

  history.replaceState = ((...args: Parameters<History["replaceState"]>) => {
    originalReplaceState(...args)
    onChange("replaceState")
  }) as History["replaceState"]

  window.addEventListener("popstate", () => onChange("popstate"))
  window.addEventListener("hashchange", () => onChange("hashchange"))
}

function isExtensionOwnedTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && Boolean(target.closest("[data-extension-owned='true']"))
}

export async function bootstrapContentObserver(): Promise<void> {
  if (isArtifactPage(window.location.href)) {
    mountArtifactFeedback(window.location.href)
    return
  }

  const settings = await getExtensionSettings()
  const rrwebSession = startRrwebSession()
  const context: ObserverContext = {
    denylist: settings.denylist,
    rrwebCount: rrwebSession.getEventCount,
    sessionId: createSessionId(),
    userId: settings.userId,
    currentToast: null
  }

  const enqueueRawEvent = async (
    eventType: ObservedEvent["event_type"],
    target: ObservedTarget,
    rawValue: string,
    extra: {
      fieldType?: string | null
      autocomplete?: string | null
      metadata?: Record<string, unknown>
    } = {}
  ) => {
    const observed = buildObservedEvent(
      {
        session_id: context.sessionId,
        user_id: context.userId,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        event_type: eventType,
        target,
        metadata: buildMetadata(context, extra.metadata),
        field_type: extra.fieldType,
        autocomplete: extra.autocomplete,
        extra_denylist: context.denylist
      },
      rawValue
    )

    if (observed) {
      await queueObservedEvent(observed)
    }
  }

  document.addEventListener("copy", (event) => {
    if (isExtensionOwnedTarget(event.target)) {
      return
    }

    const clipboardText = event.clipboardData?.getData("text/plain") ?? window.getSelection()?.toString() ?? ""
    void enqueueRawEvent("copy", buildTarget(event.target), clipboardText)
  })

  document.addEventListener("paste", (event) => {
    if (isExtensionOwnedTarget(event.target)) {
      return
    }

    const clipboardText = event.clipboardData?.getData("text/plain") ?? ""
    void enqueueRawEvent("paste", buildTarget(event.target), clipboardText)
  })

  document.addEventListener("input", (event) => {
    if (isExtensionOwnedTarget(event.target) || !(event.target instanceof Element)) {
      return
    }

    const rawValue = inferInputValue(event.target)
    const fieldType = event.target instanceof HTMLInputElement ? event.target.type : null
    const autocomplete =
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement
        ? event.target.autocomplete
        : null

    void enqueueRawEvent("input", buildTarget(event.target), rawValue, {
      fieldType,
      autocomplete,
      metadata: {
        input_name: event.target.getAttribute("name")
      }
    })
  })

  document.addEventListener("change", (event) => {
    if (isExtensionOwnedTarget(event.target) || !(event.target instanceof HTMLSelectElement)) {
      return
    }

    void enqueueRawEvent("select", buildTarget(event.target), event.target.value, {
      metadata: {
        input_name: event.target.getAttribute("name")
      }
    })
  })

  document.addEventListener(
    "submit",
    (event) => {
      if (isExtensionOwnedTarget(event.target) || !(event.target instanceof HTMLFormElement)) {
        return
      }

      const summary = `submit:${event.target.action || "current-page"}`
      void enqueueRawEvent("submit", buildTarget(event.target), summary, {
        metadata: {
          form_action: event.target.action || null,
          field_count: event.target.elements.length
        }
      })
    },
    true
  )

  document.addEventListener(
    "click",
    (event) => {
      if (isExtensionOwnedTarget(event.target)) {
        return
      }

      const target = buildTarget(event.target)
      const descriptor = [target.text, target.aria_label].filter(Boolean).join(" ").trim()
      void enqueueRawEvent(inferClickEventType(event.target), target, descriptor)
    },
    true
  )

  observeHistory((reason) => {
    void recordNavigation(context, reason)
  })

  window.addEventListener("beforeunload", () => {
    void recordNavigation(context, "beforeunload")
  })

  await recordNavigation(context, "initial-load")
}

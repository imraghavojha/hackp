import { buildObservedEvent, buildTarget } from "./capture"
import { mountArtifactFeedback } from "./feedback"
import { showInlineHelper } from "./helper-overlay"
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
  currentHelper: { dispose: () => void } | null
  lastSuggestionKey: string | null
  repeatedActionCount: number
  refreshTimers: Set<number>
  refreshInFlight: boolean
}

let fallbackSessionId: string | null = null

function createSessionId(): string {
  const storageKey = "pwa_extension_session_id"
  try {
    const existing = sessionStorage.getItem(storageKey)
    if (existing) {
      return existing
    }

    const value = crypto.randomUUID()
    sessionStorage.setItem(storageKey, value)
    return value
  } catch {
    if (fallbackSessionId === null) {
      fallbackSessionId = crypto.randomUUID()
    }
    return fallbackSessionId
  }
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

  if (
    target instanceof HTMLButtonElement &&
    /format|run|process|apply|submit/i.test([target.textContent, target.getAttribute("aria-label")].filter(Boolean).join(" "))
  ) {
    return "submit"
  }

  return "click"
}

function findNavigatingAnchor(target: EventTarget | null): HTMLAnchorElement | null {
  if (!(target instanceof Element)) {
    return null
  }

  const anchor = target.closest("a[href]")
  return anchor instanceof HTMLAnchorElement ? anchor : null
}

function clearScheduledRefreshes(context: ObserverContext) {
  for (const timerId of context.refreshTimers) {
    globalThis.clearTimeout(timerId)
  }
  context.refreshTimers.clear()
}

function scheduleRefreshBurst(
  context: ObserverContext,
  reason: string,
  options: {
    recordPageVisit?: boolean
    delays?: number[]
  } = {}
) {
  const delays = options.delays ?? [0]
  clearScheduledRefreshes(context)

  for (const delay of delays) {
    const timerId = globalThis.setTimeout(() => {
      context.refreshTimers.delete(timerId)
      void refreshSuggestion(context, {
        reason,
        recordPageVisit: Boolean(options.recordPageVisit && delay === delays[0])
      })
    }, delay)
    context.refreshTimers.add(timerId)
  }
}

async function refreshSuggestion(
  context: ObserverContext,
  options: {
    reason: string
    recordPageVisit?: boolean
  }
) {
  if (context.refreshInFlight) {
    return
  }

  context.refreshInFlight = true

  try {
    if (options.recordPageVisit) {
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
      metadata: buildMetadata(context, { reason: options.reason })
    },
    window.location.href
  )

    if (event) {
      await queueObservedEvent(event)
    }
    }

    const settings = await getExtensionSettings()
    if (isDeniedUrl(window.location.href, settings.denylist) || settings.suppressedOrigins.includes(window.location.origin)) {
      context.currentToast?.dispose()
      context.currentToast = null
      return
    }

    const response = await sendExtensionMessage({
      type: "extension/fetch-tools-for-url",
      url: window.location.href,
      allowSeedFallback: context.repeatedActionCount >= 3
    })
    const analysisResponse = await sendExtensionMessage({
      type: "extension/fetch-analysis-for-url",
      url: window.location.href
    })
    const analysis = analysisResponse.ok ? analysisResponse.analysis ?? null : null

    if (!response.ok || !response.tools || response.tools.length === 0) {
      context.currentToast?.dispose()
      context.currentToast = null
      return
    }

    const tool = pickSuggestedTool(window.location.href, response.tools)
    if (!tool) {
      return
    }

    const suggestionKey = [
      tool.id,
      analysis?.id ?? "no-analysis",
      analysis?.repetition_count ?? context.repeatedActionCount,
      window.location.href
    ].join("::")
    if (context.lastSuggestionKey === suggestionKey && context.currentToast) {
      return
    }
    context.lastSuggestionKey = suggestionKey

    context.currentToast?.dispose()
    globalThis.setTimeout(() => {
      const effectiveAnalysis =
        analysis ??
        (context.repeatedActionCount >= 3
          ? {
              id: 0,
              user_id: context.userId,
              url: window.location.href,
              signature: tool.signature ?? null,
              transformation_name: tool.name,
              summary: "I noticed you repeating the same workflow on this page.",
              confidence: null,
              repetition_count: context.repeatedActionCount,
              event_window: { start: null, end: null },
              status: "observed",
              tool_id: tool.id,
              created_at: new Date().toISOString()
            }
          : null)

      context.currentToast = showSuggestionToast(tool, window.location.origin, effectiveAnalysis, () => {
        void showInlineHelper(tool, effectiveAnalysis).then((handle) => {
          context.currentHelper?.dispose()
          context.currentHelper = handle
        })
      })
    }, POPUP_DELAY_MS)
  } finally {
    context.refreshInFlight = false
  }
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

function registerDemoActionBridge(
  context: ObserverContext,
  enqueueRawEvent: (
    eventType: ObservedEvent["event_type"],
    target: ObservedTarget,
    rawValue: string,
    extra?: {
      fieldType?: string | null
      autocomplete?: string | null
      metadata?: Record<string, unknown>
    }
  ) => Promise<void>
) {
  window.addEventListener("pwa-demo-action", (event: Event) => {
    const customEvent = event as CustomEvent<{
      event_type?: ObservedEvent["event_type"]
      value?: string
      metadata?: Record<string, unknown>
      target?: ObservedTarget
    }>
    const detail = customEvent.detail ?? {}
    const eventType = detail.event_type ?? "click"
    const target = detail.target ?? {
      tag: "demo",
      role: null,
      text: "demo-action",
      aria_label: null
    }
    void enqueueRawEvent(eventType, target, detail.value ?? "", {
      metadata: {
        source: "demo-bridge",
        ...(detail.metadata ?? {})
      }
    })
  })
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
    currentToast: null,
    currentHelper: null,
    lastSuggestionKey: null,
    repeatedActionCount: 0,
    refreshTimers: new Set<number>(),
    refreshInFlight: false
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
      if (eventType === "submit" || eventType === "file_download") {
        context.repeatedActionCount += 1
      }
      await queueObservedEvent(observed)
      if (context.repeatedActionCount >= 3) {
        scheduleRefreshBurst(context, "local-threshold", {
          delays: [2_500, 5_500]
        })
      } else if (["copy", "paste", "input", "select", "submit", "file_download"].includes(eventType)) {
        scheduleRefreshBurst(context, `${eventType}-activity`, {
          delays: [2_500]
        })
      }
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
    "pointerdown",
    (event) => {
      if (isExtensionOwnedTarget(event.target)) {
        return
      }

      const anchor = findNavigatingAnchor(event.target)
      if (!anchor) {
        return
      }

      const target = buildTarget(anchor)
      const descriptor = [target.text, target.aria_label, anchor.href].filter(Boolean).join(" ").trim()
      void enqueueRawEvent("click", target, descriptor, {
        metadata: {
          phase: "pointerdown"
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

      if (findNavigatingAnchor(event.target)) {
        return
      }

      const target = buildTarget(event.target)
      const descriptor = [target.text, target.aria_label].filter(Boolean).join(" ").trim()
      void enqueueRawEvent(inferClickEventType(event.target), target, descriptor)
    },
    true
  )

  registerDemoActionBridge(context, enqueueRawEvent)

  observeHistory((reason) => {
    context.currentHelper?.dispose()
    context.currentHelper = null
    context.lastSuggestionKey = null
    context.repeatedActionCount = 0
    scheduleRefreshBurst(context, reason, {
      recordPageVisit: true,
      delays: [0, 2_500, 5_500]
    })
  })

  window.addEventListener("beforeunload", () => {
    clearScheduledRefreshes(context)
    context.currentHelper?.dispose()
    context.currentHelper = null
  })

  window.addEventListener("focus", () => {
    scheduleRefreshBurst(context, "window-focus", {
      delays: [0]
    })
  })

  scheduleRefreshBurst(context, "initial-load", {
    recordPageVisit: true,
    delays: [0, 2_500, 5_500]
  })
}

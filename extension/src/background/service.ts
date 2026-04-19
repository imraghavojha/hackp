import { backendApi } from "./api"
import { withRetries } from "./retry"
import { FLUSH_ALARM_NAME, FLUSH_INTERVAL_MS, MAX_BUFFERED_EVENTS } from "../lib/constants"
import { clearShowcaseState, getExtensionSettings, getLibraryTools, getQueuedEvents, setLibraryTools, setQueuedEvents, updateExtensionSettings } from "../lib/storage"
import { sortLibraryTools, updateLibraryTool, upsertLibraryTools } from "../lib/library"
import type { EventsBatchRequest, ObservedEvent } from "../types/events"
import type { ExtensionMessage, ExtensionMessageResponse, ToolFeedbackPayload } from "../types/messages"

let flushInProgress = false
let flushTimeoutId: number | null = null

async function flushEvents(): Promise<void> {
  if (flushInProgress) {
    return
  }

  flushInProgress = true

  try {
    const queuedEvents = await getQueuedEvents()
    if (queuedEvents.length === 0) {
      return
    }

    const settings = await getExtensionSettings()
    const payload: EventsBatchRequest = {
      user_id: settings.userId,
      events: queuedEvents
    }

    const result = await withRetries(() => backendApi.postEvents(payload))
    if (result !== null) {
      await setQueuedEvents([])
      return
    }

    await setQueuedEvents([])
  } finally {
    flushInProgress = false
  }
}

async function queueEvents(events: ObservedEvent[]): Promise<ExtensionMessageResponse> {
  const queuedEvents = await getQueuedEvents()
  const next = [...queuedEvents, ...events]
  await setQueuedEvents(next)

  const hasImportantSignal = events.some((event) =>
    ["copy", "paste", "input", "select", "submit", "file_download", "navigation"].includes(event.event_type)
  )

  if (next.length >= MAX_BUFFERED_EVENTS || hasImportantSignal) {
    if (flushTimeoutId !== null) {
      globalThis.clearTimeout(flushTimeoutId)
    }
    flushTimeoutId = globalThis.setTimeout(() => {
      void flushEvents()
      flushTimeoutId = null
    }, 2_000)
  }

  if (next.length >= MAX_BUFFERED_EVENTS) {
    await flushEvents()
  }

  return { ok: true, accepted: events.length, buffered: next.length }
}

async function fetchToolsForUrl(url: string, allowSeedFallback = false): Promise<ExtensionMessageResponse> {
  const settings = await getExtensionSettings()
  const tools = await backendApi.getToolsForUrl(url, settings.userId, allowSeedFallback)
  const library = await getLibraryTools()
  const merged = upsertLibraryTools(library, tools, url, new Date().toISOString())
  await setLibraryTools(sortLibraryTools(merged))
  return { ok: true, tools }
}

async function fetchAnalysisForUrl(url: string): Promise<ExtensionMessageResponse> {
  const settings = await getExtensionSettings()
  const analysis = await backendApi.getAnalysisForUrl(url, settings.userId)
  return { ok: true, analysis }
}

async function openTool(toolId: string): Promise<ExtensionMessageResponse> {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
    const activeTab = tabs[0]
    if (activeTab?.id !== undefined) {
      const response = await chrome.tabs.sendMessage(activeTab.id, {
        type: "content/open-tool-inline",
        toolId
      })
      if (response?.ok) {
        const library = await getLibraryTools()
        const updated = updateLibraryTool(library, toolId, {
          last_opened_at: new Date().toISOString()
        })
        await setLibraryTools(sortLibraryTools(updated))
        return { ok: true }
      }
    }
  } catch {
    // Fall through to opening a regular tab if the content surface isn't available.
  }

  const url = backendApi.getArtifactUrl(toolId)
  await chrome.tabs.create({ url })

  const library = await getLibraryTools()
  const updated = updateLibraryTool(library, toolId, {
    last_opened_at: new Date().toISOString()
  })
  await setLibraryTools(sortLibraryTools(updated))
  return { ok: true }
}

async function listLibrary(): Promise<ExtensionMessageResponse> {
  const library = await getLibraryTools()
  return { ok: true, library: sortLibraryTools(library) }
}

async function resetShowcaseExtensionState(): Promise<ExtensionMessageResponse> {
  await clearShowcaseState()
  return { ok: true }
}

async function getSettings(): Promise<ExtensionMessageResponse> {
  const settings = await getExtensionSettings()
  return { ok: true, settings }
}

async function updateUserId(userId: string): Promise<ExtensionMessageResponse> {
  const nextUserId = userId.trim() || "bob"
  const settings = await updateExtensionSettings({ userId: nextUserId })
  return { ok: true, settings }
}

async function updateDenylist(denylist: string[]): Promise<ExtensionMessageResponse> {
  const settings = await updateExtensionSettings({
    denylist: denylist.filter(Boolean).map((entry) => entry.trim()).filter(Boolean)
  })
  return { ok: true, settings }
}

async function suppressOrigin(origin: string): Promise<ExtensionMessageResponse> {
  const settings = await getExtensionSettings()
  const suppressedOrigins = Array.from(new Set([...settings.suppressedOrigins, origin]))
  const updated = await updateExtensionSettings({ suppressedOrigins })
  return { ok: true, settings: updated }
}

async function sendFeedback(payload: ToolFeedbackPayload): Promise<ExtensionMessageResponse> {
  const settings = await getExtensionSettings()

  if (payload.feedback.trim().length > 0) {
    await backendApi.postFeedback({
      user_id: settings.userId,
      tool_id: payload.toolId,
      feedback: payload.feedback.trim(),
      context: payload.context
    })
  }

  await backendApi.postUsage(payload.toolId, {
    user_id: settings.userId,
    succeeded: payload.succeeded,
    duration_ms: payload.durationMs
  })

  const library = await getLibraryTools()
  const updated = updateLibraryTool(library, payload.toolId, {
    last_opened_at: new Date().toISOString()
  })
  await setLibraryTools(sortLibraryTools(updated))

  return { ok: true }
}

async function handleMessage(message: ExtensionMessage): Promise<ExtensionMessageResponse> {
  switch (message.type) {
    case "extension/queue-events":
      return queueEvents(message.events)
    case "extension/fetch-tools-for-url":
      return fetchToolsForUrl(message.url, message.allowSeedFallback)
    case "extension/fetch-analysis-for-url":
      return fetchAnalysisForUrl(message.url)
    case "extension/open-tool":
      return openTool(message.toolId)
    case "extension/list-library":
      return listLibrary()
    case "extension/clear-showcase-state":
      return resetShowcaseExtensionState()
    case "extension/get-settings":
      return getSettings()
    case "extension/update-user-id":
      return updateUserId(message.userId)
    case "extension/update-denylist":
      return updateDenylist(message.denylist)
    case "extension/suppress-origin":
      return suppressOrigin(message.origin)
    case "extension/tool-feedback":
      return sendFeedback(message.payload)
    default:
      return { ok: false, error: "Unsupported extension message" }
  }
}

export function registerBackgroundListeners() {
  chrome.alarms.create(FLUSH_ALARM_NAME, { periodInMinutes: FLUSH_INTERVAL_MS / 60_000 })

  chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms.create(FLUSH_ALARM_NAME, { periodInMinutes: FLUSH_INTERVAL_MS / 60_000 })
  })

  chrome.runtime.onStartup.addListener(() => {
    chrome.alarms.create(FLUSH_ALARM_NAME, { periodInMinutes: FLUSH_INTERVAL_MS / 60_000 })
  })

  chrome.alarms.onAlarm.addListener((alarm: { name?: string }) => {
    if (alarm.name === FLUSH_ALARM_NAME) {
      void flushEvents()
    }
  })

  chrome.runtime.onMessage.addListener((message: ExtensionMessage, _sender: unknown, sendResponse: (response: ExtensionMessageResponse) => void) => {
    void handleMessage(message)
      .then((response) => sendResponse(response))
      .catch((error: Error) => sendResponse({ ok: false, error: error.message }))

    return true
  })
}

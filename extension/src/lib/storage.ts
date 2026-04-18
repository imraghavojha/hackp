import { DEFAULT_DENYLIST, DEFAULT_USER_ID, STORAGE_KEYS } from "./constants"
import type { ObservedEvent } from "../types/events"
import type { ExtensionSettings } from "../types/messages"
import type { CachedToolEntry } from "../types/tools"

function storageGet<T>(key: string): Promise<T | undefined> {
  return new Promise((resolve) => {
    chrome.storage.local.get([key], (result: Record<string, T | undefined>) => {
      resolve(result[key] as T | undefined)
    })
  })
}

function storageSet(values: Record<string, unknown>): Promise<void> {
  return new Promise((resolve) => {
    chrome.storage.local.set(values, () => resolve())
  })
}

export async function getExtensionSettings(): Promise<ExtensionSettings> {
  const stored = await storageGet<Partial<ExtensionSettings>>(STORAGE_KEYS.settings)
  return {
    userId: stored?.userId ?? DEFAULT_USER_ID,
    denylist: stored?.denylist ?? DEFAULT_DENYLIST,
    suppressedOrigins: stored?.suppressedOrigins ?? []
  }
}

export async function updateExtensionSettings(patch: Partial<ExtensionSettings>): Promise<ExtensionSettings> {
  const current = await getExtensionSettings()
  const next = { ...current, ...patch }
  await storageSet({ [STORAGE_KEYS.settings]: next })
  return next
}

export async function getQueuedEvents(): Promise<ObservedEvent[]> {
  return (await storageGet<ObservedEvent[]>(STORAGE_KEYS.queue)) ?? []
}

export async function setQueuedEvents(events: ObservedEvent[]): Promise<void> {
  await storageSet({ [STORAGE_KEYS.queue]: events })
}

export async function getLibraryTools(): Promise<CachedToolEntry[]> {
  return (await storageGet<CachedToolEntry[]>(STORAGE_KEYS.library)) ?? []
}

export async function setLibraryTools(tools: CachedToolEntry[]): Promise<void> {
  await storageSet({ [STORAGE_KEYS.library]: tools })
}

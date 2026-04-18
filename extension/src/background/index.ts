import { backendApi } from "./api"
import { FLUSH_INTERVAL_MS } from "../lib/constants"
import type { EventsBatchRequest, ObservedEvent } from "../types/events"

export async function flushEvents(userId: string, events: ObservedEvent[]) {
  if (events.length === 0) {
    return { accepted: 0, buffered: 0 }
  }

  const payload: EventsBatchRequest = { user_id: userId, events }
  return backendApi.postEvents(payload)
}

export function startFlushLoop(run: () => Promise<void>) {
  return globalThis.setInterval(run, FLUSH_INTERVAL_MS)
}

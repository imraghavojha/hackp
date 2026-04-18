import type { ObservedEvent } from "../types/events"
import { isDeniedUrl, redactValue, shouldCaptureField } from "./privacy"

export function buildObservedEvent(
  base: Omit<ObservedEvent, "value"> & { field_type?: string | null },
  rawValue: string
): ObservedEvent | null {
  if (isDeniedUrl(base.url) || !shouldCaptureField(base.field_type)) {
    return null
  }

  return {
    session_id: base.session_id,
    user_id: base.user_id,
    timestamp: base.timestamp,
    url: base.url,
    event_type: base.event_type,
    target: base.target,
    value: redactValue(rawValue),
    metadata: base.metadata
  }
}

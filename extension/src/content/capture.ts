import type { ObservedEvent } from "../types/events"
import { isDeniedUrl, redactValue, shouldCaptureField } from "./privacy"

export function buildObservedEvent(
  base: Omit<ObservedEvent, "value"> & {
    field_type?: string | null
    autocomplete?: string | null
    extra_denylist?: string[]
  },
  rawValue: string
): ObservedEvent | null {
  if (isDeniedUrl(base.url, base.extra_denylist) || !shouldCaptureField(base.field_type, base.autocomplete, rawValue)) {
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

export function buildTarget(target: EventTarget | null): ObservedEvent["target"] {
  if (!(target instanceof Element)) {
    return {
      tag: null,
      role: null,
      text: null,
      aria_label: null
    }
  }

  return {
    tag: target.tagName.toLowerCase(),
    role: target.getAttribute("role"),
    text: target.textContent?.trim().slice(0, 160) ?? null,
    aria_label: target.getAttribute("aria-label")
  }
}

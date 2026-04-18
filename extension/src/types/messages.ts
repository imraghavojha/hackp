import type { ObservedEvent } from "./events"
import type { CachedToolEntry, ToolRecord } from "./tools"

export interface ExtensionSettings {
  userId: string
  denylist: string[]
  suppressedOrigins: string[]
}

export interface ToolFeedbackPayload {
  toolId: string
  feedback: string
  context: string
  succeeded: boolean
  durationMs: number
}

export type ExtensionMessage =
  | { type: "extension/queue-events"; events: ObservedEvent[] }
  | { type: "extension/fetch-tools-for-url"; url: string }
  | { type: "extension/open-tool"; toolId: string }
  | { type: "extension/list-library" }
  | { type: "extension/get-settings" }
  | { type: "extension/update-user-id"; userId: string }
  | { type: "extension/update-denylist"; denylist: string[] }
  | { type: "extension/suppress-origin"; origin: string }
  | { type: "extension/tool-feedback"; payload: ToolFeedbackPayload }

export type ExtensionMessageResponse =
  | { ok: true; accepted?: number; buffered?: number; tools?: ToolRecord[]; settings?: ExtensionSettings; library?: CachedToolEntry[] }
  | { ok: false; error: string }

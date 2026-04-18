export type ObservedEventType =
  | "click"
  | "input"
  | "navigation"
  | "copy"
  | "paste"
  | "submit"
  | "select"
  | "file_download"

export interface ObservedTarget {
  tag: string | null
  role: string | null
  text: string | null
  aria_label: string | null
}

export interface ObservedEvent {
  session_id: string
  user_id: string
  timestamp: string
  url: string
  event_type: ObservedEventType
  target: ObservedTarget
  value: string
  metadata: Record<string, unknown>
}

export interface EventsBatchRequest {
  user_id: string
  events: ObservedEvent[]
}

export interface EventsBatchResponse {
  accepted: number
  buffered: number
}

export interface ToolTrigger {
  type: "on_url_visit"
  url_pattern: string
  prompt: string
}

export interface ToolUiPrefs {
  theme?: "dark" | "light"
  density?: "compact" | "comfortable"
}

export interface ToolSummary {
  id: string
  name: string
  description: string
  trigger: ToolTrigger
  ui_prefs: ToolUiPrefs
}

export interface UsageRequest {
  user_id: string
  succeeded: boolean
  duration_ms: number
}

export interface FeedbackRequest {
  user_id: string
  tool_id: string
  feedback: string
  context: string
}

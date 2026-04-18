export interface ToolTriggerTimeWindow {
  start: string
  end: string
  timezone: string
}

export interface ToolTrigger {
  type: "on_url_visit"
  url_pattern: string
  prompt: string
  time_window?: ToolTriggerTimeWindow | null
}

export interface ToolUiPrefs {
  theme?: "dark" | "light"
  density?: "compact" | "comfortable"
  primary_label?: string
  show_preview?: boolean
}

export interface ToolStats {
  times_used: number
  last_used: string | null
  avg_duration_ms: number | null
}

export interface ToolArtifactSummary {
  artifact_id: string
  input_spec?: {
    primary_input: string
    accepts: string[]
    sample_fixture_id?: string | null
  }
  output_spec?: {
    format: string
    filename_pattern: string
  }
}

export interface ToolRecord {
  id: string
  user_id: string
  signature?: string | null
  name: string
  description: string
  created_at: string
  source_event_window?: {
    start: string | null
    end: string | null
    repetition_count: number
  }
  trigger: ToolTrigger
  ui_prefs: ToolUiPrefs
  transformation_summary: string[]
  status: string
  stats: ToolStats
  artifact: ToolArtifactSummary
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

export interface CachedToolEntry extends ToolRecord {
  last_suggested_at?: string | null
  last_opened_at?: string | null
  source_url?: string | null
}

export interface AnalysisRecord {
  id: number
  user_id: string
  url: string
  signature: string | null
  transformation_name: string | null
  summary: string
  confidence: number | null
  repetition_count: number
  event_window: {
    start: string | null
    end: string | null
  }
  status: string
  tool_id: string | null
  created_at: string
}

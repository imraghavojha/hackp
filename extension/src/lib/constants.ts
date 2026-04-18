export const BACKEND_BASE_URL = "http://127.0.0.1:8000"
export const DEFAULT_USER_ID = "bob"
export const FLUSH_INTERVAL_MS = 60_000
export const MAX_BUFFERED_EVENTS = 500
export const POPUP_DELAY_MS = 2_000
export const POPUP_TTL_MS = 20_000
export const MAX_CAPTURED_TEXT_LENGTH = 5_000
export const FLUSH_ALARM_NAME = "extension-flush-events"
export const MAX_POST_RETRIES = 3
export const DEFAULT_DENYLIST = [
  "bank",
  "payments",
  "stripe",
  "medical",
  "health",
  "dating"
]
export const STORAGE_KEYS = {
  settings: "extension.settings",
  queue: "extension.queue",
  library: "extension.library"
} as const

import type { PlasmoCSConfig } from "plasmo"

import { bootstrapContentObserver } from "../content/runtime"

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  all_frames: false,
  run_at: "document_idle"
}

void bootstrapContentObserver()

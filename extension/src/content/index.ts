import type { ToolRecord } from "../types/tools"

export function pickSuggestedTool(_url: string, tools: ToolRecord[]): ToolRecord | null {
  return tools[0] ?? null
}

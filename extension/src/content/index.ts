import type { ToolSummary } from "../types/tools"

export function pickSuggestedTool(url: string, tools: ToolSummary[]): ToolSummary | null {
  return tools.find((tool) => url.includes(tool.trigger.url_pattern)) ?? null
}

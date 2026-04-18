import type { ToolSummary } from "../types/tools"

export function renderLibraryItems(tools: ToolSummary[]): string[] {
  return tools.map((tool) => `${tool.name} :: ${tool.description}`)
}

import type { ToolSummary } from "../types/tools"

export function renderPopup(tools: ToolSummary[]): string {
  const items = tools
    .map((tool) => `<li><button data-tool-id="${tool.id}">${tool.name}</button></li>`)
    .join("")

  return `<section><h1>Your tools</h1><ul>${items}</ul></section>`
}

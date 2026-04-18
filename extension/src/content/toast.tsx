import type { ToolSummary } from "../types/tools"

export function renderToastMarkup(tool: ToolSummary): string {
  return `
    <aside data-tool-id="${tool.id}">
      <strong>${tool.name}</strong>
      <p>${tool.trigger.prompt}</p>
      <button data-action="open">Open tool</button>
      <button data-action="dismiss">Not now</button>
    </aside>
  `.trim()
}

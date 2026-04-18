import type { CachedToolEntry, ToolRecord } from "../types/tools"

export function upsertLibraryTools(
  existing: CachedToolEntry[],
  incoming: ToolRecord[],
  sourceUrl: string,
  timestamp: string
): CachedToolEntry[] {
  const byId = new Map(existing.map((tool) => [tool.id, tool]))

  for (const tool of incoming) {
    const previous = byId.get(tool.id)
    byId.set(tool.id, {
      ...previous,
      ...tool,
      source_url: sourceUrl,
      last_suggested_at: timestamp,
      last_opened_at: previous?.last_opened_at ?? null
    })
  }

  return Array.from(byId.values())
}

export function updateLibraryTool(
  existing: CachedToolEntry[],
  toolId: string,
  patch: Partial<CachedToolEntry>
): CachedToolEntry[] {
  return existing.map((tool) => (tool.id === toolId ? { ...tool, ...patch } : tool))
}

export function sortLibraryTools(tools: CachedToolEntry[]): CachedToolEntry[] {
  return [...tools].sort((left, right) => {
    const leftTime = left.last_opened_at ?? left.last_suggested_at ?? left.stats?.last_used ?? ""
    const rightTime = right.last_opened_at ?? right.last_suggested_at ?? right.stats?.last_used ?? ""
    return rightTime.localeCompare(leftTime)
  })
}

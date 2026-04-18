import type { EventsBatchRequest, EventsBatchResponse } from "../types/events"
import type { FeedbackRequest, ToolSummary, UsageRequest } from "../types/tools"

const API_BASE = "http://localhost:8000"

export const backendApi = {
  async postEvents(payload: EventsBatchRequest): Promise<EventsBatchResponse> {
    const response = await fetch(`${API_BASE}/v1/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return response.json()
  },

  async getToolsForUrl(url: string, userId: string): Promise<ToolSummary[]> {
    const response = await fetch(
      `${API_BASE}/v1/tools/for_url?url=${encodeURIComponent(url)}&user_id=${encodeURIComponent(userId)}`
    )
    const data = (await response.json()) as { tools: ToolSummary[] }
    return data.tools
  },

  getArtifactUrl(toolId: string): string {
    return `${API_BASE}/v1/tools/${toolId}/artifact`
  },

  async postUsage(toolId: string, payload: UsageRequest): Promise<{ logged: boolean }> {
    const response = await fetch(`${API_BASE}/v1/tools/${toolId}/usage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return response.json()
  },

  async postFeedback(payload: FeedbackRequest): Promise<{ stored: boolean; memory_id: string }> {
    const response = await fetch(`${API_BASE}/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return response.json()
  }
}

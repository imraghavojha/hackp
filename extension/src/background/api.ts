import type { EventsBatchRequest, EventsBatchResponse } from "../types/events"
import type { AnalysisRecord, FeedbackRequest, ToolRecord, UsageRequest } from "../types/tools"
import { BACKEND_BASE_URL } from "../lib/constants"

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const backendApi = {
  async postEvents(payload: EventsBatchRequest): Promise<EventsBatchResponse> {
    const response = await fetch(`${BACKEND_BASE_URL}/v1/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return parseJsonResponse<EventsBatchResponse>(response)
  },

  async getToolsForUrl(url: string, userId: string, allowSeedFallback = false): Promise<ToolRecord[]> {
    const params = new URLSearchParams({
      url,
      user_id: userId
    })
    if (allowSeedFallback) {
      params.set("allow_seed_fallback", "true")
    }
    const response = await fetch(
      `${BACKEND_BASE_URL}/v1/tools/for_url?${params.toString()}`
    )
    const data = await parseJsonResponse<{ tools: ToolRecord[] }>(response)
    return data.tools
  },

  async getAnalysisForUrl(url: string, userId: string): Promise<AnalysisRecord | null> {
    const response = await fetch(
      `${BACKEND_BASE_URL}/v1/analysis/for_url?url=${encodeURIComponent(url)}&user_id=${encodeURIComponent(userId)}`
    )
    const data = await parseJsonResponse<{ analysis: AnalysisRecord | null }>(response)
    return data.analysis
  },

  async getShowcaseState(): Promise<Record<string, unknown>> {
    const response = await fetch(`${BACKEND_BASE_URL}/demo/showcase/state`)
    return parseJsonResponse<Record<string, unknown>>(response)
  },

  getArtifactUrl(toolId: string): string {
    return `${BACKEND_BASE_URL}/v1/tools/${toolId}/artifact`
  },

  async postUsage(toolId: string, payload: UsageRequest): Promise<{ logged: boolean }> {
    const response = await fetch(`${BACKEND_BASE_URL}/v1/tools/${toolId}/usage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return parseJsonResponse<{ logged: boolean }>(response)
  },

  async postFeedback(payload: FeedbackRequest): Promise<{ stored: boolean; memory_id: string }> {
    const response = await fetch(`${BACKEND_BASE_URL}/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    return parseJsonResponse<{ stored: boolean; memory_id: string }>(response)
  }
}

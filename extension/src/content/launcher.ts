import { backendApi } from "../background/api"

export function getArtifactUrl(toolId: string): string {
  return backendApi.getArtifactUrl(toolId)
}

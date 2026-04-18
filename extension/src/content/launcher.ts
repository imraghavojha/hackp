import { sendExtensionMessage } from "../lib/messaging"

export async function openTool(toolId: string) {
  return sendExtensionMessage({ type: "extension/open-tool", toolId })
}

import type { ExtensionMessage, ExtensionMessageResponse } from "../types/messages"

export function sendExtensionMessage(message: ExtensionMessage): Promise<ExtensionMessageResponse> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response: ExtensionMessageResponse | undefined) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message })
        return
      }

      resolve(response ?? { ok: false, error: "No response from extension background" })
    })
  })
}

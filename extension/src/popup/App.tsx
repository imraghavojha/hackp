import { useEffect, useMemo, useState } from "react"

import { sendExtensionMessage } from "../lib/messaging"
import type { ExtensionSettings } from "../types/messages"
import type { CachedToolEntry, ToolRecord } from "../types/tools"

async function getCurrentTabUrl(): Promise<string> {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs: Array<{ url?: string }>) => {
      resolve(tabs[0]?.url ?? "")
    })
  })
}

export function PopupApp() {
  const [matchingTools, setMatchingTools] = useState<ToolRecord[]>([])
  const [libraryTools, setLibraryTools] = useState<CachedToolEntry[]>([])
  const [settings, setSettings] = useState<ExtensionSettings | null>(null)
  const [userIdValue, setUserIdValue] = useState("")
  const [denylistValue, setDenylistValue] = useState("")
  const [status, setStatus] = useState("Loading extension state...")

  useEffect(() => {
    void (async () => {
      const [settingsResponse, libraryResponse] = await Promise.all([
        sendExtensionMessage({ type: "extension/get-settings" }),
        sendExtensionMessage({ type: "extension/list-library" })
      ])

      if (settingsResponse.ok && settingsResponse.settings) {
        setSettings(settingsResponse.settings)
        setUserIdValue(settingsResponse.settings.userId)
        setDenylistValue(settingsResponse.settings.denylist.join("\n"))
      }

      if (libraryResponse.ok && libraryResponse.library) {
        setLibraryTools(libraryResponse.library)
      }

      const currentUrl = await getCurrentTabUrl()
      if (currentUrl) {
        const toolsResponse = await sendExtensionMessage({
          type: "extension/fetch-tools-for-url",
          url: currentUrl
        })

        if (toolsResponse.ok && toolsResponse.tools) {
          setMatchingTools(toolsResponse.tools)
          setStatus(
            toolsResponse.tools.length > 0
              ? `Found ${toolsResponse.tools.length} tool suggestion(s) for this page.`
              : "No matching tools for this page yet."
          )
        } else {
          setStatus("Couldn't fetch tools for the current page.")
        }
      } else {
        setStatus("Open a regular browser tab to see matching tools.")
      }
    })()
  }, [])

  const combinedTools = useMemo(() => {
    const byId = new Map<string, CachedToolEntry>()
    for (const tool of libraryTools) {
      byId.set(tool.id, tool)
    }
    for (const tool of matchingTools) {
      const previous = byId.get(tool.id)
      byId.set(tool.id, { ...previous, ...tool })
    }
    return Array.from(byId.values())
  }, [libraryTools, matchingTools])

  async function handleOpen(toolId: string) {
    await sendExtensionMessage({ type: "extension/open-tool", toolId })
    setStatus(`Opened ${toolId}.`)
  }

  async function handleSavePrivacy() {
    const denylist = denylistValue
      .split(/\n|,/)
      .map((entry) => entry.trim())
      .filter(Boolean)

    const response = await sendExtensionMessage({
      type: "extension/update-denylist",
      denylist
    })

    if (response.ok && response.settings) {
      setSettings(response.settings)
      setStatus("Saved privacy denylist.")
    } else {
      setStatus("Couldn't save privacy denylist.")
    }
  }

  async function handleSaveUserId() {
    const response = await sendExtensionMessage({
      type: "extension/update-user-id",
      userId: userIdValue
    })

    if (response.ok && response.settings) {
      setSettings(response.settings)
      setStatus(`Switched active worker to ${response.settings.userId}.`)
      const currentUrl = await getCurrentTabUrl()
      if (currentUrl) {
        const toolsResponse = await sendExtensionMessage({
          type: "extension/fetch-tools-for-url",
          url: currentUrl
        })
        if (toolsResponse.ok && toolsResponse.tools) {
          setMatchingTools(toolsResponse.tools)
        }
      }
    } else {
      setStatus("Couldn't switch active worker.")
    }
  }

  return (
    <main
      style={{
        width: 360,
        minHeight: 420,
        padding: 18,
        background: "#f3f4f6",
        color: "#111827",
        fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif'
      }}>
      <section
        style={{
          background: "#ffffff",
          border: "1px solid rgba(148, 163, 184, 0.22)",
          borderRadius: 16,
          padding: 16,
          boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)"
        }}>
        <h1 style={{ margin: "0 0 8px", fontSize: "1.1rem" }}>Personal Workflow Agent</h1>
        <p style={{ margin: 0, color: "#6b7280", fontSize: "0.9rem" }}>{status}</p>
      </section>

      <section style={{ marginTop: 16 }}>
        <h2 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Tools</h2>
        <div style={{ display: "grid", gap: 10 }}>
          {combinedTools.length === 0 ? (
            <div
              style={{
                borderRadius: 16,
                border: "1px solid rgba(148, 163, 184, 0.18)",
                padding: 14,
                color: "#6b7280",
                background: "#ffffff"
              }}>
              Visit a matching page and tool suggestions will start appearing here.
            </div>
          ) : (
            combinedTools.map((tool) => (
              <article
                key={tool.id}
                style={{
                  borderRadius: 16,
                  border: "1px solid rgba(148, 163, 184, 0.18)",
                  padding: 14,
                  background: "#ffffff",
                  boxShadow: "0 8px 18px rgba(15, 23, 42, 0.05)"
                }}>
                <div style={{ fontWeight: 700 }}>{tool.name}</div>
                <div style={{ color: "#6b7280", fontSize: "0.86rem", marginTop: 4 }}>{tool.description}</div>
                <div style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: 8 }}>
                  Last seen: {tool.last_opened_at ?? tool.last_suggested_at ?? tool.stats?.last_used ?? "not yet"}
                </div>
                <button
                  onClick={() => void handleOpen(tool.id)}
                  style={{
                    marginTop: 10,
                    border: 0,
                    borderRadius: 999,
                    background: "#1d4ed8",
                    color: "#ffffff",
                    padding: "10px 14px",
                    fontWeight: 700,
                    cursor: "pointer"
                  }}>
                  Open
                </button>
              </article>
            ))
          )}
        </div>
      </section>

      <section style={{ marginTop: 16 }}>
        <h2 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Worker</h2>
        <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: "0.84rem" }}>
          Use `bob`, `maya`, or `kai` to test the seeded personas.
        </p>
        <input
          value={userIdValue}
          onChange={(event) => setUserIdValue(event.target.value)}
          style={{
            width: "100%",
            height: 42,
            boxSizing: "border-box",
            borderRadius: 12,
            border: "1px solid rgba(148, 163, 184, 0.22)",
            background: "#ffffff",
            color: "#111827",
            padding: "0 12px",
            font: '14px/1.4 "IBM Plex Sans", sans-serif'
          }}
        />
        <button
          onClick={() => void handleSaveUserId()}
          style={{
            marginTop: 10,
            border: 0,
            borderRadius: 999,
            background: "#111827",
            color: "#ffffff",
            padding: "10px 14px",
            fontWeight: 700,
            cursor: "pointer"
          }}>
          Save worker
        </button>
      </section>

      <section style={{ marginTop: 16 }}>
        <h2 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Privacy</h2>
        <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: "0.84rem" }}>
          Current user: <strong style={{ color: "#111827" }}>{settings?.userId ?? "bob"}</strong>
        </p>
        <textarea
          value={denylistValue}
          onChange={(event) => setDenylistValue(event.target.value)}
          style={{
            width: "100%",
            minHeight: 96,
            boxSizing: "border-box",
            borderRadius: 14,
            border: "1px solid rgba(148, 163, 184, 0.22)",
            background: "#ffffff",
            color: "#111827",
            padding: 12,
            font: '13px/1.4 "IBM Plex Mono", monospace'
          }}
        />
        <button
          onClick={() => void handleSavePrivacy()}
          style={{
            marginTop: 10,
            border: 0,
            borderRadius: 999,
            background: "#1d4ed8",
            color: "#ffffff",
            padding: "10px 14px",
            fontWeight: 700,
            cursor: "pointer"
          }}>
          Save denylist
        </button>
      </section>
    </main>
  )
}

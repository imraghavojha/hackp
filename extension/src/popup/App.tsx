import { useEffect, useMemo, useState } from "react"

import { backendApi } from "../background/api"
import { sendExtensionMessage } from "../lib/messaging"
import type { ExtensionSettings } from "../types/messages"
import type { AnalysisRecord, CachedToolEntry, ToolRecord } from "../types/tools"

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
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisRecord | null>(null)
  const [settings, setSettings] = useState<ExtensionSettings | null>(null)
  const [status, setStatus] = useState("Loading extension state...")
  const [showcaseState, setShowcaseState] = useState<Record<string, any> | null>(null)
  const [currentUrl, setCurrentUrl] = useState("")

  useEffect(() => {
    const retryTimeouts = new Set<number>()

    void (async () => {
      const [settingsResponse, libraryResponse] = await Promise.all([
        sendExtensionMessage({ type: "extension/get-settings" }),
        sendExtensionMessage({ type: "extension/list-library" })
      ])

      if (settingsResponse.ok && settingsResponse.settings) {
        setSettings(settingsResponse.settings)
      }

      if (libraryResponse.ok && libraryResponse.library) {
        setLibraryTools(libraryResponse.library)
      }

      const currentUrl = await getCurrentTabUrl()
      setCurrentUrl(currentUrl)
      if (currentUrl) {
        const isShowcasePortal = currentUrl.includes("portal.example.com/leads")
        if (currentUrl.includes("portal.example.com/leads")) {
          try {
            const showcase = await backendApi.getShowcaseState()
            setShowcaseState(showcase)
          } catch {
            setShowcaseState(null)
          }
        } else {
          setShowcaseState(null)
        }

        const retryDelays = [2_500, 5_500]
        let retryIndex = 0

          const loadCurrentPageState = async () => {
            const [toolsResponse, analysisResponse] = await Promise.all([
              sendExtensionMessage({
                type: "extension/fetch-tools-for-url",
                url: currentUrl,
                allowSeedFallback: isShowcasePortal
              }),
              sendExtensionMessage({
                type: "extension/fetch-analysis-for-url",
              url: currentUrl
            })
          ])

          if (toolsResponse.ok && toolsResponse.tools) {
            setMatchingTools(toolsResponse.tools)
            setStatus(
              toolsResponse.tools.length > 0
                ? `Found ${toolsResponse.tools.length} tool suggestion(s) for this page.`
                : analysisResponse.ok && analysisResponse.analysis
                  ? "Analysis is ready for this page, but there is no helper suggestion yet."
                  : "Analyzing this page..."
            )
          } else {
            setStatus("Couldn't fetch tools for the current page.")
          }

          if (analysisResponse.ok) {
            setCurrentAnalysis(analysisResponse.analysis ?? null)
          }

          if (
            (!toolsResponse.ok || toolsResponse.tools?.length === 0) &&
            (!analysisResponse.ok || analysisResponse.analysis === null) &&
            retryIndex < retryDelays.length
          ) {
            const delay = retryDelays[retryIndex]
            retryIndex += 1
            const timeoutId = window.setTimeout(() => {
              retryTimeouts.delete(timeoutId)
              void loadCurrentPageState()
            }, delay)
            retryTimeouts.add(timeoutId)
          }
        }

        await loadCurrentPageState()
      } else {
        setStatus("Open a regular browser tab to see matching tools.")
      }
    })()

    return () => {
      for (const timeoutId of retryTimeouts) {
        window.clearTimeout(timeoutId)
      }
      retryTimeouts.clear()
    }
  }, [])

  const combinedTools = useMemo(() => {
    if (currentUrl.includes("portal.example.com/leads")) {
      return matchingTools.map((tool) => {
        if (!showcaseState) {
          return tool as CachedToolEntry
        }
        const workflow = showcaseState.workflow ?? {}
        const showcaseTool = showcaseState.tool ?? {}
        const scenes = showcaseState.scenes ?? {}
        return {
          ...tool,
          name: showcaseTool.name ?? tool.name,
          description:
            scenes.tool_generated
              ? "Current run helper: opens inline and replays this demo's latest CSV-to-Excel workflow."
              : Number(workflow.times_seen ?? 0) >= 1
                ? "Current run helper is primed from the observed workbook edits and waiting for Add code."
                : "No current-run helper yet. Finish the first workbook pass and reset remains clean."
        } as CachedToolEntry
      })
    }

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

  const showcaseSummary = useMemo(() => {
    if (!showcaseState) {
      return null
    }
    const workflow = showcaseState.workflow ?? {}
    const tool = showcaseState.tool ?? {}
    const scenes = showcaseState.scenes ?? {}
    const pending = tool.pending_update
    if (pending) {
      return `Pending update: ${pending.suggested_change}`
    }
    if (scenes.tool_generated) {
      return `Current run tool ready inline: ${tool.recipe?.formula_text ?? "formula saved"}`
    }
    if (Number(workflow.times_seen ?? 0) >= 1) {
      return "Current run remembered. Click open after Add code is offered on day two."
    }
    return "Reset is clean. No carried-over helper is shown until this run learns one."
  }, [showcaseState])

  return (
    <main
      style={{
        width: 360,
        minHeight: 420,
        padding: 18,
        background: "#111827",
        color: "#f3f4f6",
        fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif'
      }}>
      <section
        style={{
          background: "#0f172a",
          border: "1px solid rgba(148, 163, 184, 0.22)",
          borderRadius: 16,
          padding: 16,
          boxShadow: "0 10px 24px rgba(15, 23, 42, 0.24)"
        }}>
        <h1 style={{ margin: "0 0 8px", fontSize: "1.1rem" }}>Personal Workflow Agent</h1>
        <p style={{ margin: 0, color: "#9ca3af", fontSize: "0.9rem" }}>{status}</p>
        <p style={{ margin: "8px 0 0", color: "#9ca3af", fontSize: "0.82rem" }}>
          Signed in as <strong style={{ color: "#f3f4f6" }}>{settings?.userId ?? "bob"}</strong>
        </p>
        {showcaseSummary ? (
          <p style={{ margin: "8px 0 0", color: "#93c5fd", fontSize: "0.8rem", lineHeight: 1.4 }}>
            {showcaseSummary}
          </p>
        ) : null}
      </section>

      {currentAnalysis ? (
        <section style={{ marginTop: 16 }}>
          <h2 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Latest analysis</h2>
          <article
            style={{
              borderRadius: 16,
              border: "1px solid rgba(148, 163, 184, 0.18)",
              padding: 14,
              background: "#0f172a",
              boxShadow: "0 8px 18px rgba(15, 23, 42, 0.18)"
            }}>
            <div style={{ fontWeight: 700 }}>
              {currentAnalysis.transformation_name ?? "Repeated workflow detected"}
            </div>
            <div style={{ color: "#9ca3af", fontSize: "0.86rem", marginTop: 4 }}>
              {currentAnalysis.summary}
            </div>
            <div style={{ color: "#9ca3af", fontSize: "0.8rem", marginTop: 8 }}>
              Repetition count: {currentAnalysis.repetition_count}
              {" · "}
              Confidence: {currentAnalysis.confidence ?? "n/a"}
              {" · "}
              Status: {currentAnalysis.status}
            </div>
          </article>
        </section>
      ) : null}

      <section style={{ marginTop: 16 }}>
        <h2 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>Tools</h2>
        <div style={{ display: "grid", gap: 10 }}>
          {combinedTools.length === 0 ? (
            <div
              style={{
                borderRadius: 16,
                border: "1px solid rgba(148, 163, 184, 0.18)",
                padding: 14,
                color: "#9ca3af",
                background: "#0f172a"
              }}>
              {currentUrl.includes("portal.example.com/leads")
                ? "This reset is clean. Finish the first pass and the current run's helper state will appear here."
                : "Visit a matching page and tool suggestions will start appearing here."}
            </div>
          ) : (
            combinedTools.map((tool) => (
              <article
                key={tool.id}
                style={{
                  borderRadius: 16,
                  border: "1px solid rgba(148, 163, 184, 0.18)",
                  padding: 14,
                  background: "#0f172a",
                  boxShadow: "0 8px 18px rgba(15, 23, 42, 0.18)"
                }}>
                <div style={{ fontWeight: 700 }}>{tool.name}</div>
                <div style={{ color: "#9ca3af", fontSize: "0.86rem", marginTop: 4 }}>{tool.description}</div>
                <div style={{ color: "#9ca3af", fontSize: "0.8rem", marginTop: 8 }}>
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
                    padding: "13px 18px",
                    fontWeight: 700,
                    cursor: "pointer",
                    fontSize: "0.95rem"
                  }}>
                  Open
                </button>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  )
}

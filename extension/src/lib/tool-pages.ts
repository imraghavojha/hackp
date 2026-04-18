export function parseArtifactToolId(url: string): string | null {
  const match = url.match(/\/v1\/tools\/([^/]+)\/artifact/)
  return match?.[1] ?? null
}

export function isArtifactPage(url: string): boolean {
  return parseArtifactToolId(url) !== null
}

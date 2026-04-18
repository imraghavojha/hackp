import { record } from "rrweb"

export interface RrwebSession {
  stop: () => void
  getEventCount: () => number
}

export function startRrwebSession(): RrwebSession {
  let count = 0

  const stop = record({
    emit() {
      count += 1
    },
    sampling: {
      mousemove: false,
      scroll: 5_000
    } as never
  }) ?? (() => {})

  return {
    stop,
    getEventCount: () => count
  }
}

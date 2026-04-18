import { MAX_POST_RETRIES } from "../lib/constants"

export function backoffDelayMs(attempt: number): number {
  return 250 * 2 ** attempt
}

export async function withRetries<T>(operation: () => Promise<T>): Promise<T | null> {
  for (let attempt = 0; attempt < MAX_POST_RETRIES; attempt += 1) {
    try {
      return await operation()
    } catch (error) {
      if (attempt === MAX_POST_RETRIES - 1) {
        return null
      }

      await new Promise((resolve) => globalThis.setTimeout(resolve, backoffDelayMs(attempt)))
    }
  }

  return null
}

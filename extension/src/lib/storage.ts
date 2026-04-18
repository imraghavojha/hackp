import type { ObservedEvent } from "../types/events"

const memoryQueue: ObservedEvent[] = []

export function enqueueEvent(event: ObservedEvent) {
  memoryQueue.push(event)
}

export function drainEvents(): ObservedEvent[] {
  return memoryQueue.splice(0, memoryQueue.length)
}

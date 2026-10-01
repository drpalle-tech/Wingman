import type { ChatMessage } from '../types'

const STORAGE_KEY = 'wingman.history.v1'
const MAX_MESSAGES = 40

export function loadHistory(): ChatMessage[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    if (!Array.isArray(parsed)) return []
    return (parsed as ChatMessage[]).map((m) =>
      m.role === 'assistant' && m.kind === 'generation' && m.status === 'streaming' ? { ...m, status: 'stopped' } : m,
    )
  } catch {
    return []
  }
}

export function saveHistory(messages: ChatMessage[]): void {
  let kept = messages.slice(-MAX_MESSAGES)
  while (kept.length > 0) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(kept))
      return
    } catch {
      kept = kept.slice(Math.ceil(kept.length / 2)) // over the storage quota: drop the oldest half
    }
  }
  localStorage.removeItem(STORAGE_KEY)
}

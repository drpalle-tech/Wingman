import type { ChatTurn } from '@wingman/client'
import type { ChatMessage } from '../types'

const MAX_TURNS = 20
const MAX_CHARS = 40_000

/** Converts the visible conversation (chats, reviews, generations) into turns the chat model can follow. */
export function toChatTurns(messages: ChatMessage[]): ChatTurn[] {
  const turns = messages.flatMap((m) => {
    const content = describe(m)
    return content ? [{ role: m.role, content }] : []
  })
  const kept: ChatTurn[] = []
  let used = 0
  for (const turn of turns.slice(-MAX_TURNS).reverse()) {
    if (used + turn.content.length > MAX_CHARS) break
    kept.unshift(turn)
    used += turn.content.length
  }
  return kept
}

function describe(message: ChatMessage): string {
  if (message.role === 'user') {
    const text = message.text || `(${message.mode} request)`
    return message.attachments.length ? `${text}\n[Attached: ${message.attachments.join(', ')}]` : text
  }
  switch (message.kind) {
    case 'review':
      return [
        `Review summary: ${message.result.summary}`,
        ...message.result.findings.map(
          (f) => `- [${f.severity}] ${f.path}${f.start_line ? `:${f.start_line}` : ''} ${f.title}: ${f.message}`,
        ),
      ].join('\n')
    case 'generation':
      return message.status === 'error' ? '' : message.text
    case 'answer':
      return message.text
    case 'error':
      return ''
  }
}

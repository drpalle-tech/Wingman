import type { StreamEvent } from '@wingman/client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { toChatTurns } from './lib/conversation'
import { loadHistory, saveHistory } from './lib/history'
import type { AssistantRequest, ChatMessage, GenerationMessage } from './types'

const newId = () => crypto.randomUUID()

export function useAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory)
  const [busy, setBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const messagesRef = useRef(messages)

  useEffect(() => {
    messagesRef.current = messages
    if (!busy) saveHistory(messages)
  }, [messages, busy])

  useEffect(() => () => abortRef.current?.abort(), [])

  const append = useCallback((message: ChatMessage) => setMessages((prev) => [...prev, message]), [])

  const updateGeneration = useCallback((id: string, patch: Partial<GenerationMessage>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id && m.role === 'assistant' && m.kind === 'generation' ? { ...m, ...patch } : m)),
    )
  }, [])

  const streamInto = useCallback(
    async (id: string, events: AsyncGenerator<StreamEvent>) => {
      let text = ''
      let finished = false
      for await (const event of events) {
        if (event.type === 'start') {
          updateGeneration(id, { model: event.model, secretsRedacted: event.secretsRedacted })
        } else if (event.type === 'delta') {
          text += event.text
          updateGeneration(id, { text })
        } else if (event.type === 'done') {
          finished = true
          const { result } = event
          updateGeneration(id, {
            status: 'done',
            text: result.text,
            files: result.files,
            truncated: result.truncated,
            usage: result.usage,
            model: result.model,
          })
        } else {
          finished = true
          updateGeneration(id, { status: 'error', error: event.message })
        }
      }
      if (!finished) updateGeneration(id, { status: 'error', error: 'The response ended before it was complete.' })
    },
    [updateGeneration],
  )

  const send = useCallback(
    async (request: AssistantRequest) => {
      const controller = new AbortController()
      const { signal } = controller
      abortRef.current = controller
      setBusy(true)
      const history = toChatTurns(messagesRef.current)
      append({
        id: newId(),
        role: 'user',
        mode: request.mode,
        generateMode: request.mode === 'generate' ? request.generateMode : undefined,
        text: request.text,
        attachments: request.files.map((f) => f.path),
      })

      let streamId: string | null = null
      try {
        if (request.mode === 'review') {
          const result = await api.review({ context: { files: request.files }, instructions: request.text || null }, signal)
          append({ id: newId(), role: 'assistant', kind: 'review', result })
        } else if (request.mode === 'ask') {
          const answer = await api.askDocuments(request.text, signal)
          append({ id: newId(), role: 'assistant', kind: 'answer', text: answer.response, sources: answer.sources.map(String) })
        } else {
          const id = newId()
          streamId = id
          append({ id, role: 'assistant', kind: 'generation', text: '', files: [], status: 'streaming' })
          const context = { files: request.files }
          const events =
            request.mode === 'chat'
              ? api.chat({ messages: [...history, { role: 'user', content: request.text }], context }, signal)
              : api.generate({ mode: request.generateMode, request: request.text, context }, signal)
          await streamInto(id, events)
        }
      } catch (error) {
        const aborted = signal.aborted
        const text = aborted ? 'Stopped.' : error instanceof Error ? error.message : String(error)
        if (streamId) updateGeneration(streamId, aborted ? { status: 'stopped' } : { status: 'error', error: text })
        else append({ id: newId(), role: 'assistant', kind: 'error', text })
      } finally {
        abortRef.current = null
        setBusy(false)
      }
    },
    [append, streamInto, updateGeneration],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])
  const clear = useCallback(() => setMessages([]), [])

  return { messages, busy, send, stop, clear }
}

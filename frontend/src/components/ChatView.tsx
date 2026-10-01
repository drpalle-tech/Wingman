import { useEffect, useRef } from 'react'
import type { ChatMessage, UserMessage } from '../types'
import { AssistantMessageView } from './AssistantMessageView'

const MODE_LABELS: Record<UserMessage['mode'], string> = {
  chat: 'Chat',
  review: 'Review',
  generate: 'Generate',
  ask: 'Ask docs',
}

const WAITING_TEXT: Record<UserMessage['mode'], string> = {
  chat: 'Thinking…',
  review: 'Reviewing… deep reviews usually take 20–40 seconds.',
  generate: 'Starting…',
  ask: 'Thinking…',
}

interface ChatViewProps {
  messages: ChatMessage[]
  busy: boolean
  onClear: () => void
}

export function ChatView({ messages, busy, onClear }: ChatViewProps) {
  const scroller = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const last = messages[messages.length - 1]

  useEffect(() => {
    const el = scroller.current
    if (el && (nearBottom.current || last?.role === 'user')) el.scrollTop = el.scrollHeight
  }, [messages, last?.role])

  const onScroll = () => {
    const el = scroller.current
    if (el) nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }

  return (
    <div ref={scroller} onScroll={onScroll} className="flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto w-full max-w-4xl space-y-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onClear}
              disabled={busy}
              className="text-xs text-slate-500 hover:text-red-600 disabled:opacity-50"
            >
              Clear conversation
            </button>
          </div>
        )}
        {messages.map((message) =>
          message.role === 'user' ? (
            <UserBubble key={message.id} message={message} />
          ) : (
            <div key={message.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <AssistantMessageView message={message} />
            </div>
          ),
        )}
        {busy && last?.role === 'user' && (
          <p className="animate-pulse text-sm text-slate-500">{WAITING_TEXT[last.mode]}</p>
        )}
      </div>
    </div>
  )
}

function UserBubble({ message }: { message: UserMessage }) {
  const label = message.generateMode ? `${MODE_LABELS[message.mode]} · ${message.generateMode}` : MODE_LABELS[message.mode]
  return (
    <div className="flex justify-end">
      <div className="max-w-2xl rounded-xl rounded-br-sm bg-blue-600 px-4 py-3 text-white">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">{label}</p>
        {message.text && <p className="mt-1 whitespace-pre-wrap">{message.text}</p>}
        {message.attachments.length > 0 && (
          <p className="mt-1 font-mono text-xs text-blue-100">{message.attachments.join(', ')}</p>
        )}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="mx-auto max-w-2xl py-12 text-slate-700">
      <h2 className="text-xl font-semibold text-slate-900">Your senior engineer on call</h2>
      <ul className="mt-4 space-y-2 text-sm">
        <li>
          <strong>Chat</strong>: ask anything about code, design, debugging or tooling. Attach files to ask about them;
          follow-up questions can refer to earlier reviews and generated code.
        </li>
        <li>
          <strong>Review</strong>: attach files or paste code. You get findings with severity, exact lines and fixes.
          Hard-coded secrets are flagged and removed before your code reaches the model.
        </li>
        <li>
          <strong>Generate</strong>: describe new code, or attach a file to complete or refactor it.
        </li>
        <li>
          <strong>Ask docs</strong>: ask questions about PDFs uploaded in the Documents tab.
        </li>
      </ul>
      <p className="mt-4 text-sm text-slate-500">
        Tip: also attach <code>package.json</code>, a <code>.csproj</code> or <code>requirements.txt</code> so Wingman
        knows your frameworks and versions. Drag and drop works too.
      </p>
    </div>
  )
}

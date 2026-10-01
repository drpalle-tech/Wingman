import type { ContextFile, FileRole, GenerateMode } from '@wingman/client'
import { Suspense, lazy, useRef, useState, type DragEvent, type KeyboardEvent } from 'react'
import {
  MAX_FILES,
  NEXT_ROLE,
  ROLE_HELP,
  SNIPPET_LANGUAGES,
  formatSize,
  readAttachment,
  toContextFile,
  type Attachment,
  type SnippetLanguage,
} from '../lib/files'
import type { AssistantRequest, Mode } from '../types'

const CodeEditor = lazy(() => import('./CodeEditor'))

const MODES: { id: Mode; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'review', label: 'Review' },
  { id: 'generate', label: 'Generate' },
  { id: 'ask', label: 'Ask docs' },
]

const GENERATE_MODES: { id: GenerateMode; label: string }[] = [
  { id: 'new', label: 'New code' },
  { id: 'complete', label: 'Complete' },
  { id: 'refactor', label: 'Refactor' },
]

const PLACEHOLDERS: Record<Mode | GenerateMode, string> = {
  chat: 'Ask anything about code. Attach files or paste code to ask about them.',
  review: 'Optional: anything the review should focus on?',
  generate: '',
  new: 'Describe what to build, e.g. "A FastAPI endpoint that pages through orders by customer"',
  complete: 'Optional: how should the unfinished code be completed?',
  refactor: 'What should change? e.g. "Make it async and inject the repository"',
  ask: 'Ask a question about your uploaded documents…',
}

const SEND_LABELS: Record<Mode, string> = { chat: 'Send', review: 'Review', generate: 'Generate', ask: 'Ask' }

const ROLE_STYLES: Record<FileRole, string> = {
  target: 'bg-blue-100 text-blue-800',
  related: 'bg-slate-200 text-slate-700',
  config: 'bg-emerald-100 text-emerald-800',
}

const SECONDARY_BUTTON =
  'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:border-blue-400 hover:text-blue-700'

function snippetPath(language: SnippetLanguage): string {
  const extension = SNIPPET_LANGUAGES.find((l) => l.id === language)?.extension ?? 'txt'
  return `snippet.${extension}`
}

function sendBlocker(mode: Mode, generateMode: GenerateMode, hasTarget: boolean, hasText: boolean): string | null {
  if (mode === 'chat') return hasText ? null : 'Type a message.'
  if (mode === 'ask') return hasText ? null : 'Type a question about your documents.'
  if (mode === 'review') return hasTarget ? null : 'Attach a file or paste code to review.'
  if (generateMode === 'new') return hasText ? null : 'Describe what to build.'
  if (!hasTarget) return `Attach the file to ${generateMode}, or paste it as a snippet.`
  if (generateMode === 'refactor' && !hasText) return 'Describe the refactoring you want.'
  return null
}

interface ComposerProps {
  busy: boolean
  onSend: (request: AssistantRequest) => void
  onStop: () => void
}

export function Composer({ busy, onSend, onStop }: ComposerProps) {
  const [mode, setMode] = useState<Mode>('chat')
  const [generateMode, setGenerateMode] = useState<GenerateMode>('new')
  const [text, setText] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [snippetOpen, setSnippetOpen] = useState(false)
  const [snippet, setSnippet] = useState('')
  const [snippetLanguage, setSnippetLanguage] = useState<SnippetLanguage>('python')
  const [fileError, setFileError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const usesCode = mode !== 'ask'
  const files: ContextFile[] = usesCode ? attachments.map(toContextFile) : []
  if (usesCode && snippetOpen && snippet.trim()) {
    files.push({ path: snippetPath(snippetLanguage), content: snippet, language: snippetLanguage, role: 'target' })
  }
  const blocker = sendBlocker(mode, generateMode, files.some((f) => f.role === 'target'), text.trim().length > 0)
  const placeholder = PLACEHOLDERS[mode === 'generate' ? generateMode : mode]

  const addFiles = async (list: FileList) => {
    setFileError(null)
    const results = await Promise.allSettled(Array.from(list).map(readAttachment))
    const errors = results.flatMap((r) => (r.status === 'rejected' ? [String(r.reason?.message ?? r.reason)] : []))
    const merged = new Map(attachments.map((a) => [a.path, a]))
    for (const r of results) if (r.status === 'fulfilled') merged.set(r.value.path, r.value)
    const next = [...merged.values()]
    if (next.length > MAX_FILES) errors.push(`Only ${MAX_FILES} files can be attached; the rest were ignored.`)
    setAttachments(next.slice(0, MAX_FILES))
    if (errors.length) setFileError(errors.join(' '))
  }

  const submit = () => {
    if (busy || blocker) return
    onSend({ mode, generateMode, text: text.trim(), files })
    setText('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    if (usesCode && event.dataTransfer.files.length) void addFiles(event.dataTransfer.files)
  }

  return (
    <div
      onDragOver={(event) => {
        if (!usesCode) return
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`border-t border-slate-200 bg-white px-6 py-4 ${dragging ? 'ring-2 ring-inset ring-blue-400' : ''}`}
    >
      <div className="mx-auto max-w-4xl space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <Segmented options={MODES} value={mode} onChange={setMode} />
          {mode === 'generate' && (
            <Segmented options={GENERATE_MODES} value={generateMode} onChange={setGenerateMode} small />
          )}
          {usesCode && (
            <div className="ml-auto flex gap-2">
              <button type="button" className={SECONDARY_BUTTON} onClick={() => fileInput.current?.click()}>
                Attach files
              </button>
              <button type="button" className={SECONDARY_BUTTON} onClick={() => setSnippetOpen((open) => !open)}>
                {snippetOpen ? 'Hide snippet' : 'Paste code'}
              </button>
              <input
                ref={fileInput}
                type="file"
                multiple
                className="hidden"
                onChange={(event) => {
                  if (event.target.files) void addFiles(event.target.files)
                  event.target.value = ''
                }}
              />
            </div>
          )}
        </div>

        {usesCode && attachments.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {attachments.map((a) => (
              <li
                key={a.id}
                className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 py-0.5 pl-1 pr-2 text-xs"
              >
                <button
                  type="button"
                  title={`${ROLE_HELP[a.role]}. Click to change.`}
                  onClick={() =>
                    setAttachments((prev) => prev.map((x) => (x.id === a.id ? { ...x, role: NEXT_ROLE[x.role] } : x)))
                  }
                  className={`rounded-full px-2 py-0.5 font-medium ${ROLE_STYLES[a.role]}`}
                >
                  {a.role}
                </button>
                <span className="font-mono text-slate-700">{a.path}</span>
                <span className="text-slate-400">{formatSize(a.size)}</span>
                <button
                  type="button"
                  aria-label={`Remove ${a.path}`}
                  onClick={() => setAttachments((prev) => prev.filter((x) => x.id !== a.id))}
                  className="ml-1 text-slate-400 hover:text-red-600"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
        {fileError && <p className="text-xs text-red-700">{fileError}</p>}

        {usesCode && snippetOpen && (
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-xs text-slate-600">
              Language
              <select
                value={snippetLanguage}
                onChange={(event) => setSnippetLanguage(event.target.value as SnippetLanguage)}
                className="rounded border border-slate-300 px-2 py-1"
              >
                {SNIPPET_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
              <span className="text-slate-400">sent as {snippetPath(snippetLanguage)}</span>
            </label>
            <Suspense fallback={<div className="h-[220px] rounded-lg border border-slate-300 bg-slate-50" />}>
              <CodeEditor value={snippet} language={snippetLanguage} onChange={setSnippet} />
            </Suspense>
          </div>
        )}

        <div className="flex items-end gap-3">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder={placeholder}
            aria-label="Message"
            className="flex-1 resize-y rounded-lg border border-slate-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {busy ? (
            <button
              type="button"
              onClick={onStop}
              className="rounded-lg bg-slate-700 px-6 py-3 font-medium text-white hover:bg-slate-800"
            >
              Stop
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={Boolean(blocker)}
              title={blocker ?? undefined}
              className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:bg-slate-300"
            >
              {SEND_LABELS[mode]}
            </button>
          )}
        </div>
        {blocker && !busy && (mode === 'review' || mode === 'generate') && (
          <p className="text-xs text-slate-500">{blocker}</p>
        )}
      </div>
    </div>
  )
}

interface SegmentedProps<T extends string> {
  options: { id: T; label: string }[]
  value: T
  onChange: (value: T) => void
  small?: boolean
}

function Segmented<T extends string>({ options, value, onChange, small = false }: SegmentedProps<T>) {
  return (
    <div role="radiogroup" className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="radio"
          aria-checked={option.id === value}
          onClick={() => onChange(option.id)}
          className={`rounded-md font-medium ${small ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'} ${
            option.id === value ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

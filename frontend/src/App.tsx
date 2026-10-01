import { useState } from 'react'
import { ChatView } from './components/ChatView'
import { Composer } from './components/Composer'
import { DocumentsPanel } from './components/DocumentsPanel'
import { StatusBar } from './StatusBar'
import { useAssistant } from './useAssistant'

type Tab = 'assistant' | 'documents'

const TABS: { id: Tab; label: string }[] = [
  { id: 'assistant', label: 'Assistant' },
  { id: 'documents', label: 'Documents' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('assistant')
  const assistant = useAssistant()

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <span className="text-lg font-bold text-white">W</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900">Wingman</h1>
          </div>
          <p className="text-sm text-slate-500">Code review and generation for Python, C# and React</p>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-6 px-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`border-b-2 px-2 py-2 text-sm font-medium ${
                tab === t.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Kept mounted while hidden so attachments and drafts survive tab switches. */}
      <main className={tab === 'assistant' ? 'flex min-h-0 flex-1 flex-col' : 'hidden'}>
        <ChatView messages={assistant.messages} busy={assistant.busy} onClear={assistant.clear} />
        <Composer busy={assistant.busy} onSend={assistant.send} onStop={assistant.stop} />
      </main>
      {tab === 'documents' && (
        <main className="flex min-h-0 flex-1 flex-col">
          <DocumentsPanel />
        </main>
      )}

      <StatusBar />
    </div>
  )
}

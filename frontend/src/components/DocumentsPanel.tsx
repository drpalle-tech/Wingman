import type { DocumentInfo } from '@wingman/client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function DocumentsPanel() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [enabled, setEnabled] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    try {
      const result = await api.listDocuments()
      setDocuments(result.documents)
      setEnabled(result.enabled !== false)
      setError(null)
    } catch (e) {
      setError(errorText(e))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported')
      return
    }
    setUploading(true)
    try {
      await api.uploadDocument(file, file.name)
      await load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setUploading(false)
    }
  }

  const remove = async (name: string) => {
    if (!window.confirm(`Delete "${name}"?`)) return
    try {
      await api.deleteDocument(name)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto w-full max-w-4xl space-y-4">
        {!enabled ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            Document Q&A is disabled: the backend has no Azure Storage and Search settings.
          </p>
        ) : (
          <>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void upload(file)
                event.target.value = ''
              }}
            />
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:bg-slate-300"
            >
              {uploading ? 'Uploading…' : '+ Upload PDF'}
            </button>
          </>
        )}
        {error && <p className="text-sm text-red-700">{error}</p>}
        {enabled && documents.length === 0 && <p className="py-10 text-center text-slate-500">No documents uploaded yet</p>}
        <ul className="space-y-3">
          {documents.map((doc) => (
            <li
              key={doc.name}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-300"
            >
              <div>
                <p className="font-medium text-slate-900">{doc.name}</p>
                <p className="text-sm text-slate-500">
                  {(doc.size / 1024 / 1024).toFixed(2)} MB • {new Date(doc.last_modified).toLocaleDateString()}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void remove(doc.name)}
                className="rounded px-3 py-1 text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

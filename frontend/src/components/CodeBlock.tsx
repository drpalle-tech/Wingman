import { useEffect, useMemo, useState } from 'react'
import { highlightToHtml, languageForPath } from '../lib/highlight'

interface CodeBlockProps {
  code: string
  language?: string
  path?: string
  label?: string
  downloadable?: boolean
}

export function CodeBlock({ code, language, path, label, downloadable = false }: CodeBlockProps) {
  const resolvedLanguage = language ?? (path ? languageForPath(path) : undefined)
  const html = useMemo(() => highlightToHtml(code, resolvedLanguage), [code, resolvedLanguage])

  return (
    <div className="not-prose my-2 overflow-hidden rounded-lg border border-slate-200 text-sm">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-slate-100 px-3 py-1 text-xs text-slate-600">
        <span className="truncate font-mono">{label ?? path ?? resolvedLanguage ?? 'code'}</span>
        <div className="flex shrink-0 gap-1">
          <CopyButton text={code} />
          {downloadable && path && <DownloadButton text={code} path={path} />}
        </div>
      </div>
      <pre className="max-h-[32rem] overflow-auto bg-white p-3 leading-relaxed">
        {/* highlight.js escapes the source; its output contains only its own <span> markup. */}
        <code className="hljs font-mono !bg-transparent !p-0" dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    </div>
  )
}

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 1500)
    return () => clearTimeout(timer)
  }, [copied])

  return (
    <button
      type="button"
      className="rounded px-2 py-0.5 hover:bg-slate-200"
      onClick={() => navigator.clipboard.writeText(text).then(() => setCopied(true))}
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export function DownloadButton({ text, path }: { text: string; path: string }) {
  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = path.split('/').pop() || 'file.txt'
    link.click()
    URL.revokeObjectURL(url)
  }
  return (
    <button type="button" className="rounded px-2 py-0.5 hover:bg-slate-200" onClick={download}>
      Download
    </button>
  )
}

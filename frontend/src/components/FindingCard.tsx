import type { Finding, Severity } from '@wingman/client'
import { CodeBlock } from './CodeBlock'

export const SEVERITY_STYLES: Record<Severity, string> = {
  critical: 'border-red-200 bg-red-100 text-red-800',
  major: 'border-orange-200 bg-orange-100 text-orange-800',
  minor: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
}

function location(finding: Finding): string {
  if (!finding.start_line) return finding.path
  const end = finding.end_line && finding.end_line !== finding.start_line ? `-${finding.end_line}` : ''
  return `${finding.path}:${finding.start_line}${end}`
}

export function FindingCard({ finding }: { finding: Finding }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex flex-wrap items-center gap-2">
        <span className={`rounded border px-2 py-0.5 text-xs font-semibold uppercase ${SEVERITY_STYLES[finding.severity]}`}>
          {finding.severity}
        </span>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{finding.category}</span>
        {finding.source === 'secret-scan' && (
          <span className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-800">secret scan</span>
        )}
        <h3 className="font-semibold text-slate-900">{finding.title}</h3>
      </header>
      <p
        className="mt-1 font-mono text-xs text-slate-500"
        title={finding.anchored ? 'Location verified against the source' : 'Approximate location reported by the model'}
      >
        {finding.anchored ? '' : '≈ '}
        {location(finding)}
      </p>
      {finding.quote && <CodeBlock code={finding.quote} path={finding.path} label={location(finding)} />}
      <p className="mt-2 text-sm text-slate-800">{finding.message}</p>
      {finding.suggestion && (
        <p className="mt-2 text-sm text-slate-700">
          <span className="font-semibold">Fix: </span>
          {finding.suggestion}
        </p>
      )}
      {finding.suggested_code && <CodeBlock code={finding.suggested_code} path={finding.path} label="Suggested code" />}
    </article>
  )
}

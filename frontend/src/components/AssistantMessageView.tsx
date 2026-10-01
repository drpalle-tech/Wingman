import type { ReviewResponse, Severity, UsageInfo } from '@wingman/client'
import type { AssistantMessage, GenerationMessage } from '../types'
import { CodeBlock } from './CodeBlock'
import { FindingCard, SEVERITY_STYLES } from './FindingCard'
import { Markdown } from './Markdown'

const SEVERITIES: Severity[] = ['critical', 'major', 'minor', 'info']

export function AssistantMessageView({ message }: { message: AssistantMessage }) {
  switch (message.kind) {
    case 'review':
      return <ReviewView result={message.result} />
    case 'generation':
      return <GenerationView message={message} />
    case 'answer':
      return (
        <div>
          <Markdown text={message.text} />
          {message.sources.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">Sources: {message.sources.join(', ')}</p>
          )}
        </div>
      )
    case 'error':
      return <p className="text-sm text-red-700">{message.text}</p>
  }
}

function ReviewView({ result }: { result: ReviewResponse }) {
  const counts = SEVERITIES.map((s) => [s, result.findings.filter((f) => f.severity === s).length] as const)
  return (
    <div className="space-y-3">
      <p className="text-slate-800">{result.summary}</p>
      <div className="flex flex-wrap gap-2 text-xs">
        {result.findings.length === 0 && <span className="text-slate-500">No findings.</span>}
        {counts
          .filter(([, count]) => count > 0)
          .map(([severity, count]) => (
            <span key={severity} className={`rounded border px-2 py-0.5 font-medium ${SEVERITY_STYLES[severity]}`}>
              {count} {severity}
            </span>
          ))}
      </div>
      {result.findings.map((finding) => (
        <FindingCard key={finding.id} finding={finding} />
      ))}
      <UsageLine model={result.model} usage={result.usage} />
    </div>
  )
}

function GenerationView({ message }: { message: GenerationMessage }) {
  return (
    <div className="space-y-2">
      {message.status === 'streaming' && !message.text && <p className="text-sm text-slate-500">Thinking…</p>}
      {message.text && <Markdown text={message.text} />}
      {message.status === 'streaming' && message.text && <p className="text-xs text-slate-400">Writing…</p>}
      {message.status === 'stopped' && <p className="text-xs text-slate-500">Stopped.</p>}
      {message.status === 'error' && <p className="text-sm text-red-700">{message.error}</p>}
      {message.truncated && (
        <p className="text-sm text-amber-700">The answer hit the output limit and may be incomplete. Try a narrower request.</p>
      )}
      {Boolean(message.secretsRedacted) && (
        <p className="text-xs text-purple-700">
          {message.secretsRedacted} secret(s) were removed from your code before it was sent to the model.
        </p>
      )}
      {message.files.length > 0 && (
        <details className="rounded-lg border border-slate-200 bg-white p-3">
          <summary className="cursor-pointer text-sm font-medium text-slate-800">
            Files produced ({message.files.length})
          </summary>
          {message.files.map((file) => (
            <CodeBlock key={file.path} code={file.content} language={file.language} path={file.path} downloadable />
          ))}
        </details>
      )}
      {message.usage && message.model && <UsageLine model={message.model} usage={message.usage} />}
    </div>
  )
}

function UsageLine({ model, usage }: { model: string; usage: UsageInfo }) {
  return (
    <p className="text-xs text-slate-400">
      {model} · {usage.total_tokens.toLocaleString()} tokens · ${usage.cost_usd.toFixed(4)}
    </p>
  )
}

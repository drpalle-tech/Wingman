import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CodeBlock } from './CodeBlock'

const components: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children, node }) => {
    const text = String(children ?? '').replace(/\n$/, '')
    const language = /language-([\w+#.-]+)/.exec(className ?? '')?.[1]
    if (!language && !text.includes('\n')) {
      return <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.9em]">{children}</code>
    }
    const meta = (node?.data as { meta?: string } | undefined)?.meta
    const path = meta?.match(/path=["']?([^\s"']+)/)?.[1]
    return <CodeBlock code={text} language={language} path={path} downloadable={Boolean(path)} />
  },
}

export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose prose-slate max-w-none prose-code:before:content-none prose-code:after:content-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  )
}

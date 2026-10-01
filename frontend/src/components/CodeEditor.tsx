import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { StreamLanguage } from '@codemirror/language'
import { csharp } from '@codemirror/legacy-modes/mode/clike'
import CodeMirror from '@uiw/react-codemirror'
import type { SnippetLanguage } from '../lib/files'

const EXTENSIONS = {
  python: [python()],
  csharp: [StreamLanguage.define(csharp)],
  typescript: [javascript({ jsx: true, typescript: true })],
  javascript: [javascript({ jsx: true })],
} satisfies Record<SnippetLanguage, unknown[]>

export interface CodeEditorProps {
  value: string
  language: SnippetLanguage
  onChange: (value: string) => void
}

export default function CodeEditor({ value, language, onChange }: CodeEditorProps) {
  return (
    <CodeMirror
      value={value}
      height="220px"
      extensions={EXTENSIONS[language]}
      onChange={onChange}
      placeholder="Paste or type code here…"
      basicSetup={{ foldGutter: false }}
      className="overflow-hidden rounded-lg border border-slate-300 text-sm"
    />
  )
}

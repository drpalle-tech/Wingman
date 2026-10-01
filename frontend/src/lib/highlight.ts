import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import csharp from 'highlight.js/lib/languages/csharp'
import css from 'highlight.js/lib/languages/css'
import ini from 'highlight.js/lib/languages/ini'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import 'highlight.js/styles/github.css'

const LANGUAGES = { bash, csharp, css, ini, javascript, json, markdown, python, sql, typescript, xml, yaml }
for (const [name, definition] of Object.entries(LANGUAGES)) hljs.registerLanguage(name, definition)

const EXTENSIONS: Record<string, string> = {
  py: 'python',
  cs: 'csharp',
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  json: 'json',
  csproj: 'xml',
  props: 'xml',
  xml: 'xml',
  html: 'xml',
  toml: 'ini',
  yml: 'yaml',
  yaml: 'yaml',
  md: 'markdown',
  sql: 'sql',
  css: 'css',
  sh: 'bash',
}

export function languageForPath(path: string): string | undefined {
  const extension = path.split('.').pop()?.toLowerCase()
  return extension ? EXTENSIONS[extension] : undefined
}

export function highlightToHtml(code: string, language?: string): string {
  if (language && hljs.getLanguage(language)) {
    return hljs.highlight(code, { language, ignoreIllegals: true }).value
  }
  return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

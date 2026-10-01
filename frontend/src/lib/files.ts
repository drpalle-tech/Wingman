import type { ContextFile, FileRole } from '@wingman/client'

export const MAX_FILE_BYTES = 512 * 1024
export const MAX_FILES = 20

const CONFIG_FILES = [
  /^package\.json$/,
  /\.csproj$/,
  /^directory\.build\.props$/,
  /^requirements.*\.txt$/,
  /^pyproject\.toml$/,
  /^setup\.cfg$/,
  /^ruff\.toml$/,
  /^tsconfig.*\.json$/,
  /^\.editorconfig$/,
  /^\.eslintrc/,
  /^eslint\.config\./,
  /^\.prettierrc/,
  /^appsettings.*\.json$/,
]

export const NEXT_ROLE: Record<FileRole, FileRole> = { target: 'related', related: 'config', config: 'target' }

export const ROLE_HELP: Record<FileRole, string> = {
  target: 'Target: code to review or change',
  related: 'Related: supporting code for context',
  config: 'Config: manifests and tool settings (framework and version detection)',
}

export interface Attachment extends ContextFile {
  id: string
  size: number
}

export const SNIPPET_LANGUAGES = [
  { id: 'python', label: 'Python', extension: 'py' },
  { id: 'csharp', label: 'C#', extension: 'cs' },
  { id: 'typescript', label: 'TypeScript / React', extension: 'tsx' },
  { id: 'javascript', label: 'JavaScript', extension: 'js' },
] as const

export type SnippetLanguage = (typeof SNIPPET_LANGUAGES)[number]['id']

export function defaultRole(fileName: string): FileRole {
  const name = fileName.toLowerCase()
  return CONFIG_FILES.some((pattern) => pattern.test(name)) ? 'config' : 'target'
}

export async function readAttachment(file: File): Promise<Attachment> {
  if (file.size > MAX_FILE_BYTES) {
    throw new Error(`${file.name} is larger than ${MAX_FILE_BYTES / 1024} KB`)
  }
  const content = await file.text()
  if (content.includes('\u0000')) {
    throw new Error(`${file.name} looks like a binary file`)
  }
  return {
    id: crypto.randomUUID(),
    path: file.webkitRelativePath || file.name,
    content,
    language: null,
    role: defaultRole(file.name),
    size: file.size,
  }
}

export function toContextFile({ path, content, language, role }: Attachment): ContextFile {
  return { path, content, language, role }
}

export function formatSize(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`
}

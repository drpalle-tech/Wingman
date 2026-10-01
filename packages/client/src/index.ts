import type { components } from './schema.ts'
import { readServerSentEvents } from './sse.ts'

type Schemas = components['schemas']

export type ContextBundle = Schemas['ContextBundle']
export type ContextFile = Schemas['ContextFile']
export type FileRole = ContextFile['role']
export type Selection = Schemas['Selection']
export type Diagnostic = Schemas['Diagnostic']
export type ProjectInfo = Schemas['ProjectInfo']
export type ReviewRequest = Schemas['ReviewRequest']
export type ReviewResponse = Schemas['ReviewResponse']
export type FocusArea = NonNullable<ReviewRequest['focus']>[number]
export type Finding = Schemas['Finding']
export type Severity = Finding['severity']
export type GenerateRequest = Schemas['GenerateRequest']
export type GenerateMode = GenerateRequest['mode']
export type ChatRequest = Schemas['CodeChatRequest']
export type ChatTurn = Schemas['ChatTurn']
export type StreamDone = Schemas['StreamDone']
export type GeneratedFile = Schemas['GeneratedFile']
export type UsageInfo = Schemas['UsageInfo']
export type Health = Schemas['HealthCheck']
export type DocumentAnswer = Schemas['ChatResponse']

export interface DocumentInfo {
  name: string
  size: number
  last_modified: string
}

export interface DocumentList {
  documents: DocumentInfo[]
  count: number
  enabled: boolean
}

/** All-time totals across backend restarts, plus the current backend session. */
export interface UsageStats {
  model: string
  pricing_per_1k: { input: number; output: number } | null
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_requests: number
  total_cost_usd: number
  total_cost_inr: number
  average_cost_per_request: number
  average_tokens_per_request: number
  tracking_since: string | null
  session: { start_time: string; requests: number; total_tokens: number; total_cost_usd: number }
  by_model: { model: string; requests: number; total_tokens: number; total_cost_usd: number }[]
}

export type StreamEvent =
  | { type: 'start'; model: string; secretsRedacted: number }
  | { type: 'delta'; text: string }
  | { type: 'done'; result: StreamDone }
  | { type: 'error'; message: string }

export class WingmanError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'WingmanError'
    this.status = status
  }
}

export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export class WingmanClient {
  private readonly baseUrl: string
  private readonly fetchImpl: typeof fetch

  constructor(baseUrl: string = DEFAULT_BASE_URL, fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)) {
    this.baseUrl = baseUrl.replace(/\/+$/, '')
    this.fetchImpl = fetchImpl
  }

  health(): Promise<Health> {
    return this.json('GET', '/health')
  }

  review(request: ReviewRequest, signal?: AbortSignal): Promise<ReviewResponse> {
    return this.json('POST', '/v1/review', request, signal)
  }

  generate(request: GenerateRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    return this.stream('/v1/generate', request, signal)
  }

  /** Multi-turn developer chat, optionally grounded in the files in `request.context`. */
  chat(request: ChatRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    return this.stream('/v1/chat', request, signal)
  }

  /** Answers a question from uploaded PDFs (document Q&A). */
  askDocuments(query: string, signal?: AbortSignal): Promise<DocumentAnswer> {
    return this.json('POST', '/chat', { query }, signal)
  }

  listDocuments(): Promise<DocumentList> {
    return this.json('GET', '/documents')
  }

  async uploadDocument(file: Blob, filename: string): Promise<void> {
    const form = new FormData()
    form.append('file', file, filename)
    await this.send('POST', '/upload', form)
  }

  async deleteDocument(name: string): Promise<void> {
    await this.send('DELETE', `/documents/${encodeURIComponent(name)}`)
  }

  usage(): Promise<UsageStats> {
    return this.json('GET', '/usage')
  }

  private async *stream(path: string, body: unknown, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    const response = await this.send('POST', path, body, signal)
    if (!response.body) throw new WingmanError('The server returned an empty stream')
    for await (const { event, data } of readServerSentEvents(response.body)) {
      const payload = JSON.parse(data)
      if (event === 'start') yield { type: 'start', model: payload.model, secretsRedacted: payload.secrets_redacted }
      else if (event === 'delta') yield { type: 'delta', text: payload.text }
      else if (event === 'done') yield { type: 'done', result: payload as StreamDone }
      else if (event === 'error') yield { type: 'error', message: payload.message }
    }
  }

  private async json<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    const response = await this.send(method, path, body, signal)
    return (await response.json()) as T
  }

  private async send(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
    const init: RequestInit = { method, signal }
    if (body instanceof FormData) {
      init.body = body
    } else if (body !== undefined) {
      init.body = JSON.stringify(body)
      init.headers = { 'Content-Type': 'application/json' }
    }

    let response: Response
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, init)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      throw new WingmanError(`Cannot reach the Wingman backend at ${this.baseUrl}. Is it running?`)
    }
    if (!response.ok) {
      const message = await errorMessage(response)
      if (response.status === 404 && message === 'Not Found') {
        throw new WingmanError(
          `The backend at ${this.baseUrl} has no ${method} ${path} endpoint. It is probably running older code; restart it.`,
          404,
        )
      }
      throw new WingmanError(message, response.status)
    }
    return response
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`).join('; ')
    }
  } catch {
    // Not JSON; fall through to the status text.
  }
  return `Request failed (${response.status} ${response.statusText})`
}

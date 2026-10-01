import type { ContextFile, GeneratedFile, GenerateMode, ReviewResponse, UsageInfo } from '@wingman/client'

export type Mode = 'chat' | 'review' | 'generate' | 'ask'

export interface AssistantRequest {
  mode: Mode
  generateMode: GenerateMode
  text: string
  files: ContextFile[]
}

export interface UserMessage {
  id: string
  role: 'user'
  mode: Mode
  generateMode?: GenerateMode
  text: string
  attachments: string[]
}

export interface ReviewMessage {
  id: string
  role: 'assistant'
  kind: 'review'
  result: ReviewResponse
}

export interface GenerationMessage {
  id: string
  role: 'assistant'
  kind: 'generation'
  text: string
  files: GeneratedFile[]
  status: 'streaming' | 'done' | 'stopped' | 'error'
  truncated?: boolean
  secretsRedacted?: number
  usage?: UsageInfo
  model?: string
  error?: string
}

export interface AnswerMessage {
  id: string
  role: 'assistant'
  kind: 'answer'
  text: string
  sources: string[]
}

export interface ErrorMessage {
  id: string
  role: 'assistant'
  kind: 'error'
  text: string
}

export type AssistantMessage = ReviewMessage | GenerationMessage | AnswerMessage | ErrorMessage
export type ChatMessage = UserMessage | AssistantMessage

import assert from 'node:assert/strict'
import { test } from 'node:test'

import { WingmanClient, WingmanError, type StreamEvent } from '../src/index.ts'

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

function clientReturning(response: Response, seen: Request[] = []): WingmanClient {
  return new WingmanClient('http://backend.test/', async (input, init) => {
    seen.push(new Request(input, init))
    return response
  })
}

test('generate parses events split across arbitrary chunk boundaries', async () => {
  const done = { text: 'hi', files: [], truncated: false, secrets_redacted: 0, model: 'm', usage: { input_tokens: 1, output_tokens: 2, total_tokens: 3, cost_usd: 0 } }
  const body = [
    'event: start\ndata: {"model": "m", "secrets_redacted": 2}\n\n',
    'event: delta\ndata: {"text": "h"}\n\nevent: del',
    'ta\r\ndata: {"text": "i"}\r\n\r\n',
    `event: done\ndata: ${JSON.stringify(done)}\n\n`,
  ]
  const seen: Request[] = []
  const client = clientReturning(new Response(streamOf(body), { headers: { 'Content-Type': 'text/event-stream' } }), seen)

  const events: StreamEvent[] = []
  for await (const event of client.generate({ mode: 'new', request: 'say hi' })) events.push(event)

  assert.deepEqual(events, [
    { type: 'start', model: 'm', secretsRedacted: 2 },
    { type: 'delta', text: 'h' },
    { type: 'delta', text: 'i' },
    { type: 'done', result: done },
  ])
  assert.equal(seen[0].url, 'http://backend.test/v1/generate')
  assert.equal(seen[0].headers.get('content-type'), 'application/json')
})

test('chat streams from the code chat endpoint, documents from the PDF endpoint', async () => {
  const seen: Request[] = []
  const sse = 'event: delta\ndata: {"text": "ok"}\n\n'
  const chatClient = clientReturning(new Response(streamOf([sse])), seen)
  const events: StreamEvent[] = []
  for await (const event of chatClient.chat({ messages: [{ role: 'user', content: 'hi' }] })) events.push(event)
  assert.deepEqual(events, [{ type: 'delta', text: 'ok' }])

  const docsClient = clientReturning(new Response(JSON.stringify({ response: 'a', sources: [], conversation_id: 's' })), seen)
  await docsClient.askDocuments('what is in the spec?')
  assert.deepEqual(
    seen.map((r) => new URL(r.url).pathname),
    ['/v1/chat', '/chat'],
  )
})

test('validation errors are flattened into a readable message', async () => {
  const detail = [{ loc: ['body', 'context', 'files'], msg: 'at least one target', type: 'value_error' }]
  const client = clientReturning(new Response(JSON.stringify({ detail }), { status: 422 }))
  await assert.rejects(
    client.review({ context: { files: [] } }),
    (error: unknown) => error instanceof WingmanError && error.status === 422 && error.message === 'context.files: at least one target',
  )
})

test('server error detail strings are passed through', async () => {
  const client = clientReturning(new Response(JSON.stringify({ detail: 'Model provider error (429)' }), { status: 429 }))
  await assert.rejects(client.health(), { name: 'WingmanError', message: 'Model provider error (429)' })
})

test('a missing route explains that the backend is out of date', async () => {
  const client = clientReturning(new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 }))
  await assert.rejects(client.health(), /has no GET \/health endpoint\. It is probably running older code; restart it\./)
})

test('network failures explain that the backend is unreachable', async () => {
  const client = new WingmanClient('http://127.0.0.1:1', async () => {
    throw new TypeError('fetch failed')
  })
  await assert.rejects(client.health(), /Cannot reach the Wingman backend at http:\/\/127\.0\.0\.1:1/)
})

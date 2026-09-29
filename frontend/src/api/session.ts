import { ensureOk } from './http'

export type SessionClearState = 'started' | 'success' | 'error'

export interface SessionClearEvent {
  state: SessionClearState
  message?: string
}

export interface ClearSessionOptions {
  signal?: AbortSignal
  onEvent?: (event: SessionClearEvent) => void
}

interface SseFrame {
  event: string
  data: string
}

function parseSseFrame(frame: string): SseFrame | null {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator >= 0 ? line.slice(0, separator) : line
    let value = separator >= 0 ? line.slice(separator + 1) : ''
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') event = value
    if (field === 'data') dataLines.push(value)
  }

  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}

function parseSessionClearEvent(frame: SseFrame): SessionClearEvent | null {
  if (!['started', 'success', 'error'].includes(frame.event)) return null

  let payload: unknown
  try {
    payload = JSON.parse(frame.data)
  } catch {
    throw new Error(`清空 SSE 数据不是合法 JSON: ${frame.data}`)
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`清空 SSE 数据格式非法: ${frame.data}`)
  }

  const state = (payload as { state?: unknown }).state
  if (state !== 'started' && state !== 'success' && state !== 'error') {
    throw new Error(`清空 SSE 状态非法: ${String(state)}`)
  }
  const message = (payload as { message?: unknown }).message
  return {
    state,
    message: typeof message === 'string' ? message : undefined,
  }
}

/** 通过 POST 建立 SSE 流并等待清空终态。 */
export async function clearSession(options: ClearSessionOptions = {}): Promise<void> {
  const response = await ensureOk(
    await fetch('/api/session/clear', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { Accept: 'text/event-stream' },
      signal: options.signal,
    }),
  )

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.toLowerCase().startsWith('text/event-stream')) {
    throw new Error(`清空响应类型非法: ${contentType || '缺少 Content-Type'}`)
  }
  if (!response.body) {
    throw new Error('服务器未返回可读取的清空响应流')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  function processFrame(frameText: string): boolean {
    const frame = parseSseFrame(frameText)
    if (!frame) return false
    const event = parseSessionClearEvent(frame)
    if (!event) return false
    options.onEvent?.(event)
    if (event.state === 'success') return true
    if (event.state === 'error') {
      throw new Error(event.message || '清空失败')
    }
    return false
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      if (!value) continue
      buffer += decoder.decode(value, { stream: true })
      buffer = buffer.replace(/\r\n/g, '\n')

      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const frameText = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        if (processFrame(frameText)) return
        boundary = buffer.indexOf('\n\n')
      }
    }

    buffer += decoder.decode()
    if (processFrame(buffer)) return
    throw new Error('清空响应在完成前结束')
  } finally {
    reader.releaseLock()
  }
}

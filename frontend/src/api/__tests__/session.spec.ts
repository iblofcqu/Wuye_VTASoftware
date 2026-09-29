import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../http'
import { clearSession } from '../session'

function sseResponse(chunks: string[], init: ResponseInit = {}): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
    ...init,
  })
}

describe('clearSession', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('解析跨 chunk 的 SSE 事件并等待成功', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      sseResponse([
        'event: star',
        'ted\ndata: {"state":"star',
        'ted"}\n\nevent: success\r\n',
        'data: {"state":"success"}\r\n\r\n',
      ]),
    )
    vi.stubGlobal('fetch', fetchMock)
    const events: string[] = []

    await expect(clearSession({ onEvent: (event) => events.push(event.state) })).resolves.toBeUndefined()

    expect(events).toEqual(['started', 'success'])
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/session/clear',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'text/event-stream' },
      }),
    )
  })

  it('收到 error 事件时抛出服务端原因', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([
          'event: started\ndata: {"state":"started"}\n\n',
          'event: error\ndata: {"state":"error","message":"模拟删除失败"}\n\n',
        ]),
      ),
    )

    await expect(clearSession()).rejects.toThrow('模拟删除失败')
  })

  it('非 2xx 响应保留服务端 detail 和状态码', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: '当前会话存在排队或运行中的任务，无法清空' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const error = await clearSession().catch((reason: unknown) => reason)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, message: '当前会话存在排队或运行中的任务，无法清空' })
  })

  it('拒绝缺少 body、错误响应类型和未完成就结束的流', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
    })))
    await expect(clearSession()).rejects.toThrow('未返回可读取')

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not-sse', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })))
    await expect(clearSession()).rejects.toThrow('响应类型非法')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse(['event: started\ndata: {"state":"started"}\n\n'])),
    )
    await expect(clearSession()).rejects.toThrow('完成前结束')
  })

  it('非法事件数据显式失败，未知事件被忽略', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse(['event: success\ndata: not-json\n\n'])),
    )
    await expect(clearSession()).rejects.toThrow('不是合法 JSON')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([
          'event: progress\ndata: {"state":"progress"}\n\n',
          'event: success\ndata: {"state":"success"}\n\n',
        ]),
      ),
    )
    await expect(clearSession()).resolves.toBeUndefined()
  })
})

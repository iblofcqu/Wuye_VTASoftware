import { beforeEach, describe, expect, it, vi } from 'vitest'

import { findPending, uploadFile } from '../uploader'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function memoryStorage() {
  const data = new Map<string, string>()
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value)
    },
    removeItem: (key: string) => {
      data.delete(key)
    },
    clear: () => data.clear(),
  }
}

const file = new File([new Uint8Array([1, 2, 3, 4, 5, 6])], 'scan.xyz')

const initPayload = {
  upload_id: 'u1',
  filename: 'scan.xyz',
  kind: 'pointcloud',
  size: 6,
  chunk_size: 4,
  total_chunks: 2,
  received: 0,
  received_indices: [],
  missing_indices: [0, 1],
  status: 'uploading',
  expires_at: '',
}

const completedPayload = {
  upload_id: 'u1',
  status: 'completed',
  artifact: { id: 'a1', name: 'scan.xyz', kind: 'pointcloud', size: 6, created_at: 'now' },
}

describe('uploader resume & retry', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('localStorage', memoryStorage())
  })

  it('分片失败按指数退避重试后成功', async () => {
    let attempts = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL) => {
        const url = String(input)
        if (url === '/api/uploads') return jsonResponse(initPayload, 201)
        if (url.endsWith('/chunks/0')) {
          attempts += 1
          if (attempts < 3) return jsonResponse({ detail: '网络错误' }, 500)
          return jsonResponse({ upload_id: 'u1' })
        }
        if (url.endsWith('/chunks/1')) return jsonResponse({ upload_id: 'u1' })
        if (url.endsWith('/complete')) return jsonResponse(completedPayload)
        throw new Error(`unexpected ${url}`)
      }),
    )

    const result = await uploadFile(file, { chunkSize: 4, retryAttempts: 3, retryDelayMs: 1, concurrency: 1 })
    expect(attempts).toBe(3)
    expect(result.status).toBe('done')
    expect(result.artifact?.id).toBe('a1')
  })

  it('中断后再次上传同一文件只补缺失分片', async () => {
    const calls: string[] = []
    let failChunk1 = true
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        calls.push(`${method} ${url}`)
        if (url === '/api/uploads') return jsonResponse(initPayload, 201)
        if (url.endsWith('/chunks/0')) return jsonResponse({ upload_id: 'u1' })
        if (url.endsWith('/chunks/1')) {
          return failChunk1 ? jsonResponse({ detail: '连接中断' }, 500) : jsonResponse({ upload_id: 'u1' })
        }
        if (url === '/api/uploads/u1') {
          return jsonResponse({
            ...initPayload,
            received: 1,
            received_indices: [0],
            missing_indices: [1],
          })
        }
        if (url.endsWith('/complete')) return jsonResponse(completedPayload)
        throw new Error(`unexpected ${url}`)
      }),
    )

    await expect(
      uploadFile(file, { chunkSize: 4, retryAttempts: 1, retryDelayMs: 1, concurrency: 1 }),
    ).rejects.toThrow()
    expect(findPending(file)?.uploadId).toBe('u1')

    failChunk1 = false
    const firstRunLength = calls.length
    const result = await uploadFile(file, { chunkSize: 4, retryAttempts: 1, retryDelayMs: 1, concurrency: 1 })
    const secondRunCalls = calls.slice(firstRunLength)

    expect(result.status).toBe('done')
    expect(secondRunCalls.some((call) => call.includes('/chunks/0'))).toBe(false)
    expect(secondRunCalls.some((call) => call.includes('/chunks/1'))).toBe(true)
    expect(findPending(file)).toBeUndefined()
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { runWithConcurrency, sha256Hex, uploadFile, uploadFiles } from '../uploader'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const file = new File([new Uint8Array([1, 2, 3, 4, 5, 6])], 'scan.xyz')

describe('uploader', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('按分片上传并回调进度', async () => {
    const calls: string[] = []
    const progress: number[] = []
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url === '/api/uploads') {
        return jsonResponse(
          {
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
          },
          201,
        )
      }
      if (url.startsWith('/api/uploads/u1/chunks/')) {
        expect(init?.headers).toMatchObject({ 'X-Chunk-SHA256': expect.stringMatching(/^[0-9a-f]{64}$/) })
        return jsonResponse({ upload_id: 'u1', received: 1, total_chunks: 2, received_indices: [0], missing_indices: [1] })
      }
      if (url === '/api/uploads/u1/complete') {
        return jsonResponse({
          upload_id: 'u1',
          status: 'completed',
          artifact: { id: 'a1', name: 'scan.xyz', kind: 'pointcloud', size: 6, created_at: 'now' },
        })
      }
      throw new Error(`unexpected ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await uploadFile(file, {
      chunkSize: 4,
      concurrency: 1,
      onUpdate: (state) => progress.push(state.uploadedChunks),
    })

    expect(result.status).toBe('done')
    expect(result.artifact?.id).toBe('a1')
    expect(calls).toEqual([
      'POST /api/uploads',
      'PUT /api/uploads/u1/chunks/0',
      'PUT /api/uploads/u1/chunks/1',
      'POST /api/uploads/u1/complete',
    ])
    expect(progress.at(-1)).toBe(2)
  })

  it('多文件中单个失败不影响其他文件', async () => {
    const ok = new File([new Uint8Array([9])], 'ok.xyz')
    const bad = new File([new Uint8Array([8])], 'bad.xyz')
    let initCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL) => {
        const url = String(input)
        if (url === '/api/uploads') {
          initCount += 1
          if (initCount === 2) return jsonResponse({ detail: '不支持的文件类型: .xyz' }, 400)
          return jsonResponse({
            upload_id: 'u-ok',
            filename: 'ok.xyz',
            kind: 'pointcloud',
            size: 1,
            chunk_size: 1024,
            total_chunks: 1,
            received: 0,
            received_indices: [],
            missing_indices: [0],
            status: 'uploading',
            expires_at: '',
          })
        }
        if (url === '/api/uploads/u-ok/chunks/0') return jsonResponse({ upload_id: 'u-ok' })
        if (url === '/api/uploads/u-ok/complete') {
          return jsonResponse({ upload_id: 'u-ok', status: 'completed', artifact: { id: 'a-ok', name: 'ok.xyz', kind: 'pointcloud', size: 1, created_at: 'now' } })
        }
        throw new Error(`unexpected ${url}`)
      }),
    )

    const results = await uploadFiles([ok, bad], { chunkSize: 1024 })
    expect(results[0].status).toBe('fulfilled')
    expect(results[1].status).toBe('rejected')
  })

  it('runWithConcurrency 限制并发数', async () => {
    let active = 0
    let maxActive = 0
    await runWithConcurrency([1, 2, 3, 4], 2, async () => {
      active += 1
      maxActive = Math.max(maxActive, active)
      await new Promise((resolve) => setTimeout(resolve, 5))
      active -= 1
    })
    expect(maxActive).toBeLessThanOrEqual(2)
  })

  it('非安全上下文下仍能计算 SHA-256', async () => {
    vi.stubGlobal('crypto', {})
    try {
      await expect(sha256Hex(new Uint8Array([0, 1, 2, 3]).buffer)).resolves.toBe(
        '054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8',
      )
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

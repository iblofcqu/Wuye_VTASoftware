import { beforeEach, describe, expect, it, vi } from 'vitest'

import { pollJob } from '../jobs'
import type { Job } from '@/types'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function makeJob(status: Job['status'], done = 0, total = 4): Job {
  return {
    id: 'j1',
    tool: 'quality-assess',
    status,
    created_at: 'now',
    updated_at: 'now',
    progress: { stage: `第${done}/${total}步`, done, total },
  }
}

describe('pollJob', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('轮询到成功并回调每次更新', async () => {
    vi.useFakeTimers()
    const queue = [makeJob('running', 1), makeJob('running', 2), makeJob('succeeded', 4)]
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(queue.shift() ?? makeJob('succeeded', 4))))

    const updates: string[] = []
    const promise = pollJob('j1', {
      intervalMs: 1000,
      onUpdate: (job) => updates.push(`${job.status}:${job.progress?.done}`),
    })
    await vi.advanceTimersByTimeAsync(2500)
    const final = await promise

    expect(final.status).toBe('succeeded')
    expect(updates).toEqual(['running:1', 'running:2', 'succeeded:4'])
    vi.useRealTimers()
  })

  it('失败终态直接返回并携带错误', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ ...makeJob('failed'), error: '体素尺寸必须为正数' })))
    const final = await pollJob('j1', { intervalMs: 1 })
    expect(final.status).toBe('failed')
    expect(final.error).toContain('体素尺寸')
  })

  it('abort 后停止轮询', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn(async () => jsonResponse(makeJob('running', 1)))
    vi.stubGlobal('fetch', fetchMock)

    const controller = new AbortController()
    const promise = pollJob('j1', { intervalMs: 1000, signal: controller.signal })
    await vi.advanceTimersByTimeAsync(1500)
    controller.abort()

    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
    const callsAfterAbort = fetchMock.mock.calls.length
    await vi.advanceTimersByTimeAsync(3000)
    expect(fetchMock.mock.calls.length).toBe(callsAfterAbort)
    vi.useRealTimers()
  })
})

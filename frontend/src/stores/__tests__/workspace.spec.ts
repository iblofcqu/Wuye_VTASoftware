import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '../workspace'
import type { SessionSnapshot } from '@/types'

const snapshot: SessionSnapshot = {
  session_id: 's1',
  created_at: '2026-09-29T00:00:00+00:00',
  artifacts: [
    { id: 'a1', name: 'scan.xyz', kind: 'pointcloud', size: 10, created_at: '2026-09-29T00:00:00+00:00' },
  ],
  jobs: [],
  uploads: [],
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('refresh 载入会话快照并可查询产物', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(snapshot)))
    const store = useWorkspaceStore()

    await store.refresh()

    expect(store.error).toBe('')
    expect(store.artifacts).toHaveLength(1)
    expect(store.artifactById('a1')?.name).toBe('scan.xyz')
  })

  it('失败时记录服务端 detail 且不写入快照', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: '会话不存在' }, 404)))
    const store = useWorkspaceStore()

    await store.refresh()

    expect(store.error).toBe('会话不存在')
    expect(store.snapshot).toBeNull()
    expect(store.loading).toBe(false)
  })
})

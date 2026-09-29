import { getJob } from '@/api'
import type { Job } from '@/types'

export interface PollJobOptions {
  intervalMs?: number
  onUpdate?: (job: Job) => void
  signal?: AbortSignal
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    function onAbort() {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

export const TERMINAL_STATUSES: Job['status'][] = ['succeeded', 'failed', 'interrupted']

/** 轮询任务直到进入终态；可用 AbortSignal 取消（组件卸载时）。 */
export async function pollJob(jobId: string, options: PollJobOptions = {}): Promise<Job> {
  const interval = options.intervalMs ?? 1000
  for (;;) {
    const job = await getJob(jobId)
    options.onUpdate?.(job)
    if (TERMINAL_STATUSES.includes(job.status)) return job
    await delay(interval, options.signal)
  }
}

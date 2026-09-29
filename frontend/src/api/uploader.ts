import { completeUpload, getUpload, initUpload, putChunk } from '@/api'
import type { Artifact } from '@/types'

export type UploadStatus = 'uploading' | 'completing' | 'done' | 'error'

export interface UploadItemState {
  file: File
  status: UploadStatus
  uploadedChunks: number
  totalChunks: number
  uploadedBytes: number
  error?: string
  artifact?: Artifact
  uploadId?: string
}

export interface UploadOptions {
  chunkSize?: number
  concurrency?: number
  retryAttempts?: number
  retryDelayMs?: number
  resume?: boolean
  onUpdate?: (state: UploadItemState) => void
}

export interface PendingUpload {
  uploadId: string
  fingerprint: string
  name: string
  size: number
  lastModified: number
  createdAt: number
}

const PENDING_KEY = 'wuye.uploads.v1'

function storageAvailable(): boolean {
  return typeof localStorage !== 'undefined'
}

export function fileFingerprint(file: File): string {
  return `${file.name}|${file.size}|${file.lastModified}`
}

function readPending(): PendingUpload[] {
  if (!storageAvailable()) return []
  try {
    const raw = localStorage.getItem(PENDING_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as PendingUpload[]) : []
  } catch {
    return []
  }
}

function writePending(items: PendingUpload[]): void {
  if (!storageAvailable()) return
  localStorage.setItem(PENDING_KEY, JSON.stringify(items))
}

export function rememberPending(file: File, uploadId: string): void {
  const fingerprint = fileFingerprint(file)
  const items = readPending().filter((item) => item.fingerprint !== fingerprint)
  items.push({
    uploadId,
    fingerprint,
    name: file.name,
    size: file.size,
    lastModified: file.lastModified,
    createdAt: Date.now(),
  })
  writePending(items)
}

export function forgetPending(file: File): void {
  const fingerprint = fileFingerprint(file)
  writePending(readPending().filter((item) => item.fingerprint !== fingerprint))
}

export function findPending(file: File): PendingUpload | undefined {
  const fingerprint = fileFingerprint(file)
  return readPending().find((item) => item.fingerprint === fingerprint)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** 失败重试（指数退避），用于网络不稳定场景。 */
export async function withRetry<T>(fn: () => Promise<T>, attempts = 3, baseDelayMs = 200): Promise<T> {
  let lastError: unknown
  for (let attempt = 1; attempt <= Math.max(1, attempts); attempt += 1) {
    try {
      return await fn()
    } catch (error) {
      lastError = error
      if (attempt < attempts) await sleep(baseDelayMs * 2 ** (attempt - 1))
    }
  }
  throw lastError
}

export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

export async function runWithConcurrency<T>(
  items: T[],
  limit: number,
  worker: (item: T) => Promise<void>,
): Promise<void> {
  const queue = [...items]
  let failed = false
  const size = Math.max(1, Math.min(limit, queue.length))
  const runners = Array.from({ length: size }, async () => {
    while (!failed && queue.length > 0) {
      const item = queue.shift() as T
      try {
        await worker(item)
      } catch (error) {
        failed = true
        throw error
      }
    }
  })
  await Promise.all(runners)
}

/** 分片上传单个文件：初始化 → 仅补缺失分片 → 完成合并（返回登记后的产物）。 */
export async function uploadFile(file: File, options: UploadOptions = {}): Promise<UploadItemState> {
  const state: UploadItemState = {
    file,
    status: 'uploading',
    uploadedChunks: 0,
    totalChunks: 0,
    uploadedBytes: 0,
  }
  const notify = () => options.onUpdate?.({ ...state })
  notify()

  try {
    let record = undefined as Awaited<ReturnType<typeof initUpload>> | undefined
    if (options.resume !== false) {
      const pending = findPending(file)
      if (pending) {
        try {
          const status = await getUpload(pending.uploadId)
          if (status.status === 'uploading' || status.status === 'completing' || status.status === 'completed') {
            record = status
          }
        } catch {
          record = undefined // 上传记录失效（过期/被取消）→ 重新初始化
        }
      }
    }
    if (!record) {
      record = await initUpload({
        filename: file.name,
        size: file.size,
        chunk_size: options.chunkSize,
      })
    }
    rememberPending(file, record.upload_id)
    state.uploadId = record.upload_id
    state.totalChunks = record.total_chunks
    state.uploadedChunks = record.received_indices.length
    notify()

    await runWithConcurrency(record.missing_indices, options.concurrency ?? 2, async (index) => {
      const start = index * record.chunk_size
      const blob = file.slice(start, Math.min(start + record.chunk_size, file.size))
      const buffer = await blob.arrayBuffer()
      const hash = await sha256Hex(buffer)
      await withRetry(
        () => putChunk(record.upload_id, index, blob, hash),
        options.retryAttempts ?? 3,
        options.retryDelayMs ?? 200,
      )
      state.uploadedChunks += 1
      state.uploadedBytes += blob.size
      notify()
    })

    state.status = 'completing'
    notify()
    const completed = await completeUpload(record.upload_id)
    forgetPending(file)
    state.status = 'done'
    state.artifact = completed.artifact
    notify()
    return state
  } catch (error) {
    state.status = 'error'
    state.error = error instanceof Error ? error.message : String(error)
    notify()
    throw error
  }
}

/** 多文件独立上传：单个文件失败不影响其他文件。 */
export async function uploadFiles(
  files: File[],
  options: UploadOptions = {},
): Promise<PromiseSettledResult<UploadItemState>[]> {
  return Promise.allSettled(files.map((file) => uploadFile(file, options)))
}

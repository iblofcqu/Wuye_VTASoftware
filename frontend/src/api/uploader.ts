import { completeUpload, initUpload, putChunk } from '@/api'
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
  onUpdate?: (state: UploadItemState) => void
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
    const record = await initUpload({
      filename: file.name,
      size: file.size,
      chunk_size: options.chunkSize,
    })
    state.uploadId = record.upload_id
    state.totalChunks = record.total_chunks
    notify()

    await runWithConcurrency(record.missing_indices, options.concurrency ?? 2, async (index) => {
      const start = index * record.chunk_size
      const blob = file.slice(start, Math.min(start + record.chunk_size, file.size))
      const buffer = await blob.arrayBuffer()
      const hash = await sha256Hex(buffer)
      await putChunk(record.upload_id, index, blob, hash)
      state.uploadedChunks += 1
      state.uploadedBytes += blob.size
      notify()
    })

    state.status = 'completing'
    notify()
    const completed = await completeUpload(record.upload_id)
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

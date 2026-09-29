import type { Job, SessionSnapshot, UploadRecord } from '@/types'
import { ensureOk, fetchJson, sendJson } from './http'

export const getSession = () => fetchJson<SessionSnapshot>('/api/session')

export const initUpload = (payload: { filename: string; size: number; chunk_size?: number }) =>
  sendJson<UploadRecord>('/api/uploads', 'POST', payload)

export const getUpload = (uploadId: string) => fetchJson<UploadRecord>(`/api/uploads/${uploadId}`)

export const cancelUpload = (uploadId: string) =>
  fetchJson<UploadRecord>(`/api/uploads/${uploadId}`, { method: 'DELETE' })

export async function putChunk(
  uploadId: string,
  index: number,
  data: Blob,
  sha256: string,
): Promise<UploadRecord> {
  const response = await ensureOk(
    await fetch(`/api/uploads/${uploadId}/chunks/${index}`, {
      method: 'PUT',
      credentials: 'same-origin',
      headers: { 'X-Chunk-SHA256': sha256 },
      body: data,
    }),
  )
  return (await response.json()) as UploadRecord
}

export const completeUpload = (uploadId: string) =>
  fetchJson<UploadRecord>(`/api/uploads/${uploadId}/complete`, { method: 'POST' })

export const submitJob = (tool: string, inputs: Record<string, string>, params: Record<string, unknown>) =>
  sendJson<Job>(`/api/tools/${tool}/jobs`, 'POST', { inputs, params })

export const getJob = (jobId: string) => fetchJson<Job>(`/api/jobs/${jobId}`)

export const artifactDownloadUrl = (artifactId: string) => `/api/artifacts/${artifactId}/download`

export const artifactPreviewUrl = (artifactId: string) => `/api/artifacts/${artifactId}/preview`

export const jobPreviewUrl = (jobId: string) => `/api/jobs/${jobId}/preview`

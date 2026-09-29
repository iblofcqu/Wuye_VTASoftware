export type ArtifactKind = 'mesh' | 'pointcloud' | 'report'

export interface Artifact {
  id: string
  name: string
  kind: ArtifactKind
  size: number
  created_at: string
  source_job?: string | null
}

export interface JobProgress {
  stage: string
  done: number
  total: number
  updated_at?: string
}

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'interrupted'

export interface Job {
  id: string
  tool: string
  status: JobStatus
  created_at: string
  updated_at: string
  error?: string | null
  result?: { artifacts: Artifact[]; summary: Record<string, unknown> } | null
  params?: Record<string, unknown>
  progress?: JobProgress
}

export interface UploadRecord {
  upload_id: string
  filename: string
  kind: string
  size: number
  chunk_size: number
  total_chunks: number
  received: number
  received_indices: number[]
  missing_indices: number[]
  status: string
  expires_at: string
  artifact_id?: string | null
}

export interface SessionSnapshot {
  session_id: string
  created_at: string
  artifacts: Artifact[]
  jobs: Job[]
  uploads: UploadRecord[]
}

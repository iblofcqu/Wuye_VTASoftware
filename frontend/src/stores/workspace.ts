import { defineStore } from 'pinia'

import { getSession } from '@/api'
import type { Artifact, Job, SessionSnapshot, UploadRecord } from '@/types'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    snapshot: null as SessionSnapshot | null,
    loading: false,
    error: '',
  }),
  getters: {
    artifacts: (state): Artifact[] => state.snapshot?.artifacts ?? [],
    jobs: (state): Job[] => state.snapshot?.jobs ?? [],
    uploads: (state): UploadRecord[] => state.snapshot?.uploads ?? [],
  },
  actions: {
    async refresh() {
      this.loading = true
      this.error = ''
      try {
        this.snapshot = await getSession()
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    artifactById(id: string): Artifact | undefined {
      return this.artifacts.find((artifact) => artifact.id === id)
    },
  },
})

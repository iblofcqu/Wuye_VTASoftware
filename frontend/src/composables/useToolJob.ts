import { ref } from 'vue'

import { submitJob } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Job } from '@/types'

/** 页面通用：提交工具任务并跟踪完成结果。 */
export function useToolJob() {
  const workspace = useWorkspaceStore()
  const jobId = ref<string | null>(null)
  const finishedJob = ref<Job | null>(null)
  const submitting = ref(false)
  const error = ref('')

  async function run(tool: string, inputs: Record<string, string>, params: Record<string, unknown>) {
    error.value = ''
    finishedJob.value = null
    submitting.value = true
    try {
      const job = await submitJob(tool, inputs, params)
      jobId.value = job.id
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      submitting.value = false
    }
  }

  function onFinished(job: Job) {
    finishedJob.value = job
    void workspace.refresh()
  }

  return { workspace, jobId, finishedJob, submitting, error, run, onFinished }
}

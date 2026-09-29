<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { pollJob } from '@/api/jobs'
import type { Job } from '@/types'

const props = withDefaults(defineProps<{ jobId?: string | null; intervalMs?: number }>(), {
  jobId: null,
  intervalMs: 1000,
})

const emit = defineEmits<{
  (event: 'update', job: Job): void
  (event: 'finished', job: Job): void
}>()

const job = ref<Job | null>(null)
const error = ref('')
let controller: AbortController | null = null

watch(
  () => props.jobId,
  (jobId) => {
    controller?.abort()
    controller = null
    job.value = null
    error.value = ''
    if (!jobId) return

    const current = new AbortController()
    controller = current
    pollJob(jobId, {
      intervalMs: props.intervalMs,
      signal: current.signal,
      onUpdate: (value) => {
        job.value = value
        emit('update', value)
      },
    })
      .then((final) => emit('finished', final))
      .catch((reason: unknown) => {
        if (current.signal.aborted) return
        error.value = reason instanceof Error ? reason.message : String(reason)
      })
  },
  { immediate: true },
)

onBeforeUnmount(() => controller?.abort())

const percentage = computed(() => {
  const progress = job.value?.progress
  if (!progress || !progress.total) return 0
  return Math.round((progress.done / progress.total) * 100)
})

const tagType = computed(() => {
  switch (job.value?.status) {
    case 'succeeded':
      return 'success'
    case 'failed':
    case 'interrupted':
      return 'danger'
    case 'running':
      return 'warning'
    default:
      return 'info'
  }
})
</script>

<template>
  <el-card v-if="job || error" shadow="never" class="job-progress">
    <template #header>
      <div class="job-header">
        <span>任务进度</span>
        <el-tag v-if="job" :type="tagType" size="small">{{ job.status }}</el-tag>
      </div>
    </template>

    <template v-if="job">
      <p v-if="job.progress" class="job-stage">
        {{ job.progress.stage }}（{{ job.progress.done }}/{{ job.progress.total }}）
      </p>
      <el-progress
        :percentage="percentage"
        :status="job.status === 'failed' || job.status === 'interrupted' ? 'exception' : undefined"
      />
      <el-alert
        v-if="job.error"
        type="error"
        :closable="false"
        show-icon
        class="job-error"
        :title="job.error"
      />
      <el-alert
        v-if="job.status === 'interrupted' && !job.error"
        type="error"
        :closable="false"
        show-icon
        class="job-error"
        title="服务重启导致任务中断"
      />
    </template>
    <el-alert v-else-if="error" type="error" :closable="false" show-icon :title="error" />
  </el-card>
</template>

<style scoped>
.job-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.job-stage {
  margin: 0 0 8px;
  color: #606266;
  font-size: 13px;
}

.job-error {
  margin-top: 12px;
}
</style>

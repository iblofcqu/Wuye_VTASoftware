<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { artifactDownloadUrl, artifactPreviewUrl } from '@/api'
import ArtifactPicker from '@/components/ArtifactPicker.vue'
import JobProgress from '@/components/JobProgress.vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'
import { useToolJob } from '@/composables/useToolJob'
import type { Job } from '@/types'

const coarse = useToolJob()
const fine = useToolJob()
const workspace = coarse.workspace

const activeTab = ref('coarse')
const coarseMoving = ref('')
const coarseFixed = ref('')
const voxelSize = ref('0.3')
const fineMoving = ref('')
const fineFixed = ref('')
const threshold1 = ref('0.05')
const threshold2 = ref('0.03')
const threshold3 = ref('0.005')
const handoff = ref('')

onMounted(() => void workspace.refresh())

const current = computed(() => (activeTab.value === 'coarse' ? coarse : fine))
const resultArtifact = computed(() => current.value.finishedJob.value?.result?.artifacts?.[0] ?? null)

const previewLayers = computed(() => {
  const layers: { url: string; color?: string }[] = []
  if (resultArtifact.value) layers.push({ url: artifactPreviewUrl(resultArtifact.value.id), color: 'red' })
  const fixed = activeTab.value === 'coarse' ? coarseFixed.value : fineFixed.value
  if (fixed) layers.push({ url: artifactPreviewUrl(fixed), color: 'blue' })
  return layers
})

function startCoarse() {
  void coarse.run(
    'register-fpfh',
    { moving: coarseMoving.value, fixed: coarseFixed.value },
    { voxel_size: Number(voxelSize.value) },
  )
}

function startFine() {
  void fine.run(
    'register-icp',
    { moving: fineMoving.value, fixed: fineFixed.value },
    {
      thresholds: [Number(threshold1.value), Number(threshold2.value), Number(threshold3.value)],
    },
  )
}

function onCoarseFinished(job: Job) {
  coarse.onFinished(job)
  const artifact = job.result?.artifacts?.[0]
  if (job.status === 'succeeded' && artifact) {
    fineMoving.value = artifact.id
    if (!fineFixed.value && coarseFixed.value) fineFixed.value = coarseFixed.value
    handoff.value = `已自动选择粗配准结果：${artifact.name}`
  }
}
</script>

<template>
  <el-card shadow="never">
    <template #header><b>配准</b></template>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="粗配准（FPFH）" name="coarse">
        <el-form label-width="120px">
          <el-form-item label="待配准点云">
            <ArtifactPicker v-model="coarseMoving" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="固定点云">
            <ArtifactPicker v-model="coarseFixed" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="体素大小">
            <el-input v-model="voxelSize" style="width: 200px" />
            <span class="hint">默认 0.3；配准效果不理想时可调整后重试</span>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="coarse.submitting.value"
              :disabled="!coarseMoving || !coarseFixed"
              @click="startCoarse"
            >
              开始配准
            </el-button>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="coarse.error.value"
          type="error"
          :closable="false"
          show-icon
          :title="coarse.error.value"
          class="block"
        />
        <JobProgress v-if="coarse.jobId.value" :job-id="coarse.jobId.value" @finished="onCoarseFinished" />
      </el-tab-pane>

      <el-tab-pane label="精配准（ICP）" name="fine">
        <el-alert v-if="handoff" type="info" :closable="false" show-icon :title="handoff" class="block" />
        <el-form label-width="120px">
          <el-form-item label="待配准点云">
            <ArtifactPicker v-model="fineMoving" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="固定点云">
            <ArtifactPicker v-model="fineFixed" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="精配阈值(m)">
            <el-input v-model="threshold1" style="width: 110px" />
            <el-input v-model="threshold2" style="width: 110px; margin-left: 8px" />
            <el-input v-model="threshold3" style="width: 110px; margin-left: 8px" />
            <span class="hint">默认 0.05 / 0.03 / 0.005，左值应大于右值</span>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="fine.submitting.value"
              :disabled="!fineMoving || !fineFixed"
              @click="startFine"
            >
              开始配准
            </el-button>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="fine.error.value"
          type="error"
          :closable="false"
          show-icon
          :title="fine.error.value"
          class="block"
        />
        <JobProgress v-if="fine.jobId.value" :job-id="fine.jobId.value" @finished="fine.onFinished" />
      </el-tab-pane>
    </el-tabs>

    <div v-if="resultArtifact" class="result">
      <h4>结果预览（红：待配准结果；蓝：固定点云）</h4>
      <PointCloudViewer :layers="previewLayers" />
      <p class="download">
        <el-link type="primary" :href="artifactDownloadUrl(resultArtifact.id)">
          下载 {{ resultArtifact.name }}
        </el-link>
      </p>
    </div>
  </el-card>
</template>

<style scoped>
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.block {
  margin-bottom: 12px;
}

.result {
  margin-top: 16px;
}

.download {
  margin-top: 8px;
}
</style>

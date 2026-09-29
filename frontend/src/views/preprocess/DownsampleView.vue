<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { artifactDownloadUrl, artifactPreviewUrl } from '@/api'
import ArtifactPicker from '@/components/ArtifactPicker.vue'
import JobProgress from '@/components/JobProgress.vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'
import { useToolJob } from '@/composables/useToolJob'

const workspace = useToolJob().workspace
const voxel = useToolJob()
const uniform = useToolJob()

const activeTab = ref('voxel')
const voxelInput = ref('')
const voxelSize = ref('0.01')
const uniformInput = ref('')
const everyK = ref('2')

onMounted(() => void workspace.refresh())

const current = computed(() => (activeTab.value === 'voxel' ? voxel : uniform))
const resultArtifact = computed(() => current.value.finishedJob.value?.result?.artifacts?.[0] ?? null)

function startVoxel() {
  void voxel.run('downsample-voxel', { input: voxelInput.value }, { voxel_size: Number(voxelSize.value) })
}

function startUniform() {
  void uniform.run('downsample-uniform', { input: uniformInput.value }, { every_k: Number(everyK.value) })
}
</script>

<template>
  <el-card shadow="never">
    <template #header><b>下采样</b></template>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="体素下采样" name="voxel">
        <el-form label-width="120px">
          <el-form-item label="输入点云">
            <ArtifactPicker v-model="voxelInput" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="体素尺寸">
            <el-input v-model="voxelSize" style="width: 200px" />
            <span class="hint">体素尺寸越大，下采样程度越高（默认 0.01）</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="voxel.submitting.value" :disabled="!voxelInput" @click="startVoxel">
              开始下采样
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="均匀下采样" name="uniform">
        <el-form label-width="120px">
          <el-form-item label="输入点云">
            <ArtifactPicker v-model="uniformInput" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
          </el-form-item>
          <el-form-item label="采样间隔">
            <el-input v-model="everyK" style="width: 200px" />
            <span class="hint">采样间隔越大，下采样程度越高（默认 2）</span>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="uniform.submitting.value"
              :disabled="!uniformInput"
              @click="startUniform"
            >
              开始下采样
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <el-alert
      v-if="current.error.value"
      type="error"
      :closable="false"
      show-icon
      :title="current.error.value"
      class="block"
    />
    <JobProgress
      v-if="current.jobId.value"
      :key="current.jobId.value"
      :job-id="current.jobId.value"
      @finished="current.onFinished"
    />

    <div v-if="resultArtifact" class="result">
      <h4>结果预览</h4>
      <PointCloudViewer :layers="[{ url: artifactPreviewUrl(resultArtifact.id), color: 'blue' }]" />
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

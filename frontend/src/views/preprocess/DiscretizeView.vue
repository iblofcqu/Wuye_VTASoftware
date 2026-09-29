<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { artifactDownloadUrl, artifactPreviewUrl } from '@/api'
import ArtifactPicker from '@/components/ArtifactPicker.vue'
import JobProgress from '@/components/JobProgress.vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'
import { useToolJob } from '@/composables/useToolJob'

const { workspace, jobId, finishedJob, submitting, error, run, onFinished } = useToolJob()

const meshId = ref('')
const distance = ref('0.2')

onMounted(() => {
  void workspace.refresh()
})

const resultArtifact = computed(() => finishedJob.value?.result?.artifacts?.[0] ?? null)

function start() {
  void run('mesh-discretize', { input: meshId.value }, { distance_points: Number(distance.value) })
}
</script>

<template>
  <el-card shadow="never">
    <template #header><b>网格离散</b></template>

    <el-form label-width="120px">
      <el-form-item label="网格文件">
        <ArtifactPicker v-model="meshId" kind="mesh" accept=".stl,.ply,.obj,.off,.gltf,.glb" />
      </el-form-item>
      <el-form-item label="点云间距">
        <el-input v-model="distance" style="width: 200px" />
        <span class="hint">离散后点云的平均间距（默认 0.2）</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" :disabled="!meshId" @click="start">
          开始离散
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" class="block" />
    <JobProgress v-if="jobId" :job-id="jobId" @finished="onFinished" />

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

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { artifactDownloadUrl, artifactPreviewUrl } from '@/api'
import ArtifactPicker from '@/components/ArtifactPicker.vue'
import JobProgress from '@/components/JobProgress.vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'
import { useToolJob } from '@/composables/useToolJob'

const { workspace, jobId, finishedJob, submitting, error, run, onFinished } = useToolJob()

const inputId = ref('')
const originUnit = ref('m')
const targetUnit = ref('mm')
const units = ['m', 'dm', 'cm', 'mm']

onMounted(() => void workspace.refresh())

const resultArtifact = computed(() => finishedJob.value?.result?.artifacts?.[0] ?? null)

function start() {
  void run('scale', { input: inputId.value }, { origin_unit: originUnit.value, target_unit: targetUnit.value })
}
</script>

<template>
  <el-card shadow="never">
    <template #header><b>尺寸缩放</b></template>

    <el-form label-width="120px">
      <el-form-item label="待转换点云">
        <ArtifactPicker v-model="inputId" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
      </el-form-item>
      <el-form-item label="原始单位">
        <el-select v-model="originUnit" style="width: 140px">
          <el-option v-for="unit in units" :key="unit" :label="unit" :value="unit" />
        </el-select>
      </el-form-item>
      <el-form-item label="目标单位">
        <el-select v-model="targetUnit" style="width: 140px">
          <el-option v-for="unit in units" :key="unit" :label="unit" :value="unit" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" :disabled="!inputId" @click="start">
          开始转换
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

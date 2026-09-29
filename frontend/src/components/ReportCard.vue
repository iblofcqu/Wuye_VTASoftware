<script setup lang="ts">
import { computed } from 'vue'

import { artifactDownloadUrl } from '@/api'
import type { Job } from '@/types'
import { findReportArtifact } from '@/utils/qa'

const props = defineProps<{ job: Job | null }>()

const report = computed(() => findReportArtifact(props.job))
</script>

<template>
  <el-card v-if="report" shadow="never" class="report-card">
    <template #header><b>几何质量评估报告</b></template>
    <p class="report-name">{{ report.name }}</p>
    <el-link type="primary" :href="artifactDownloadUrl(report.id)">下载 PDF 报告</el-link>
    <p class="report-note">报告中的统计数字与图表来自本次计算，与页面结果一致。</p>
  </el-card>
</template>

<style scoped>
.report-name {
  margin: 0 0 8px;
  color: #303133;
}

.report-note {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
}
</style>

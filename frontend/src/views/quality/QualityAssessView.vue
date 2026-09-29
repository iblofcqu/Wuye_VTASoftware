<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { jobPreviewUrl } from '@/api'
import ArtifactPicker from '@/components/ArtifactPicker.vue'
import DeviationHistogram from '@/components/DeviationHistogram.vue'
import JobProgress from '@/components/JobProgress.vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'
import ReportCard from '@/components/ReportCard.vue'
import { useToolJob } from '@/composables/useToolJob'
import { formatDeviationMetrics } from '@/utils/qa'

const { workspace, jobId, finishedJob, submitting, error, run, onFinished } = useToolJob()

const confirmedCloud = ref(false)
const confirmedDownsample = ref(false)
const confirmedUnit = ref(false)
const confirmedRegistration = ref(false)
const ready = computed(
  () => confirmedCloud.value && confirmedDownsample.value && confirmedUnit.value && confirmedRegistration.value,
)

const scanId = ref('')
const bimId = ref('')
const unit = ref('m')
const method = ref('Point2Point')
const distance = ref('0.01')
const ratio = ref('0.05')

onMounted(() => void workspace.refresh())

const summary = computed<Record<string, unknown> | null>(
  () => (finishedJob.value?.result?.summary as Record<string, unknown> | undefined) ?? null,
)
const figure = computed<Record<string, unknown> | null>(
  () => (summary.value?.figure as Record<string, unknown> | undefined) ?? null,
)
const metrics = computed(() => formatDeviationMetrics(summary.value))
function start() {
  void run(
    'quality-assess',
    { scan: scanId.value, bim: bimId.value },
    {
      unit: unit.value,
      method: method.value,
      distance: Number(distance.value),
      ratio: Number(ratio.value),
    },
  )
}
</script>

<template>
  <el-card shadow="never">
    <template #header><b>几何质量评估</b></template>

    <el-divider content-position="left">步骤1：预处理信息确认</el-divider>
    <el-checkbox v-model="confirmedCloud">我已获取离散点云</el-checkbox>
    <el-checkbox v-model="confirmedDownsample">我已完成下采样（可忽略）</el-checkbox>
    <el-checkbox v-model="confirmedUnit">我已检查离散点云和扫描点云单位一致</el-checkbox>
    <el-checkbox v-model="confirmedRegistration">我已进行扫描点云和离散点云的匹配</el-checkbox>

    <template v-if="ready">
      <el-divider content-position="left">步骤2：数据信息输入</el-divider>
      <el-form label-width="140px">
        <el-form-item label="扫描点云">
          <ArtifactPicker v-model="scanId" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
        </el-form-item>
        <el-form-item label="BIM 点云">
          <ArtifactPicker v-model="bimId" kind="pointcloud" accept=".xyz,.asc,.txt,.xls" />
        </el-form-item>
        <el-form-item label="点云单位">
          <el-select v-model="unit" style="width: 140px">
            <el-option v-for="item in ['m', 'dm', 'cm', 'mm']" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="偏差计算方法">
          <el-select v-model="method" style="width: 200px">
            <el-option label="Point2Point" value="Point2Point" />
            <el-option label="Point2Plane" value="Point2Plane" />
          </el-select>
        </el-form-item>
        <el-form-item label="平面邻域大小">
          <el-input v-model="distance" style="width: 200px" />
          <span class="hint">仅 Point2Plane 有效（默认 0.01）</span>
        </el-form-item>
        <el-form-item label="剔除比例">
          <el-input v-model="ratio" style="width: 200px" />
          <span class="hint">剔除偏差最大的点占比（默认 0.05）</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="!scanId || !bimId" @click="start">
            计算偏差并生成报告
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" class="block" />
      <JobProgress v-if="jobId" :job-id="jobId" @finished="onFinished" />

      <div v-if="finishedJob?.status === 'succeeded'" class="result">
        <el-divider content-position="left">步骤3：偏差统计结果</el-divider>
        <DeviationHistogram :figure="figure" :metrics="metrics" />
        <h4>偏差云图预览</h4>
        <PointCloudViewer :layers="[{ url: jobPreviewUrl(finishedJob.id) }]" />
        <ReportCard :job="finishedJob" />
      </div>
    </template>
    <el-empty v-else description="请先完成步骤1的全部确认" />
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

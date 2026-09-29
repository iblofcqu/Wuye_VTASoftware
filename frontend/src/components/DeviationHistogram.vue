<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Plotly from 'plotly.js-dist-min'

import type { MetricItem } from '@/utils/qa'

const props = defineProps<{
  figure: Record<string, unknown> | null
  metrics?: MetricItem[]
  height?: number
}>()

const chart = ref<HTMLDivElement | null>(null)

async function renderFigure() {
  await nextTick()
  if (!chart.value || !props.figure) return
  const data = (props.figure.data ?? []) as unknown[]
  const layout = {
    ...(props.figure.layout as Record<string, unknown> | undefined),
    autosize: true,
    height: props.height ?? 360,
  }
  await Plotly.react(chart.value, data, layout, { displaylogo: false, responsive: true })
}

watch(() => props.figure, () => void renderFigure(), { deep: true, immediate: true })

onBeforeUnmount(() => {
  if (chart.value) Plotly.purge(chart.value)
})
</script>

<template>
  <div class="deviation-histogram">
    <el-row v-if="metrics?.length" :gutter="12" class="metrics">
      <el-col v-for="item in metrics" :key="item.label" :span="6">
        <el-card shadow="never" class="metric-card">
          <p class="metric-label">{{ item.label }}</p>
          <p class="metric-value">{{ item.value }}</p>
        </el-card>
      </el-col>
    </el-row>
    <div ref="chart" class="chart" />
    <el-empty v-if="!figure" description="暂无偏差统计结果" />
  </div>
</template>

<style scoped>
.metrics {
  margin-bottom: 12px;
}

.metric-card {
  text-align: center;
}

.metric-label {
  margin: 0;
  font-size: 12px;
  color: #909399;
}

.metric-value {
  margin: 6px 0 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.chart {
  width: 100%;
}
</style>

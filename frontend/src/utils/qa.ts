export interface MetricItem {
  label: string
  value: string
}

/** 与基线页面一致的四项偏差统计指标。 */
export function formatDeviationMetrics(summary: Record<string, unknown> | null | undefined): MetricItem[] {
  if (!summary) return []
  const ratio = Number(summary.ratio ?? 0)
  return [
    { label: '检测点数', value: String(summary.check_num ?? 0) },
    { label: `剔除${ratio}后最大值`, value: `${Number(summary.error_max_cut ?? 0).toFixed(2)}` },
    { label: '最大值', value: `${Number(summary.error_max ?? 0).toFixed(2)}` },
    { label: '平均值', value: `${Number(summary.error_mean ?? 0).toFixed(2)}` },
  ]
}

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

import type { Artifact, Job } from '@/types'

/** 从任务结果中提取 PDF 报告产物（kind=report）。 */
export function findReportArtifact(job: Job | null | undefined): Artifact | null {
  return job?.result?.artifacts?.find((artifact) => artifact.kind === 'report') ?? null
}

/** 选择浏览器展示直方图，优先使用受限的 ui_figure，兼容旧的 figure 字段。 */
export function selectHistogramFigure(
  summary: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null {
  if (!isFigure(summary?.ui_figure)) return isFigure(summary?.figure) ? summary.figure : null
  return summary.ui_figure
}

/**
 * Plotly must receive plain JSON data. Passing Vue reactive proxies can make the
 * browser renderer spin while it walks the proxy graph, so clone at this boundary.
 */
export function toPlainFigure(figure: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(figure)) as Record<string, unknown>
}

function isFigure(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

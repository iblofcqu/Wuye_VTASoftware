import { describe, expect, it } from 'vitest'

import { findReportArtifact, formatDeviationMetrics } from '../qa'

describe('formatDeviationMetrics', () => {
  it('与基线四项指标一致', () => {
    const metrics = formatDeviationMetrics({
      check_num: 900,
      error_max_cut: 12.34,
      error_max: 20,
      error_mean: 5.67,
      ratio: 0.05,
    })
    expect(metrics).toEqual([
      { label: '检测点数', value: '900' },
      { label: '剔除0.05后最大值', value: '12.34' },
      { label: '最大值', value: '20.00' },
      { label: '平均值', value: '5.67' },
    ])
  })

  it('无效输入返回空数组', () => {
    expect(formatDeviationMetrics(null)).toEqual([])
  })
})

describe('findReportArtifact', () => {
  it('提取 kind=report 的产物', () => {
    const job = {
      id: 'j1',
      tool: 'quality-assess',
      status: 'succeeded' as const,
      created_at: 'now',
      updated_at: 'now',
      result: {
        artifacts: [
          { id: 'a1', name: 'scan_VD.xyz', kind: 'pointcloud' as const, size: 1, created_at: 'now' },
          { id: 'a2', name: 'scan几何质量评估报告2026929.pdf', kind: 'report' as const, size: 2, created_at: 'now' },
        ],
        summary: {},
      },
    }
    expect(findReportArtifact(job)?.name).toBe('scan几何质量评估报告2026929.pdf')
    expect(findReportArtifact(null)).toBeNull()
  })
})

<template>
  <el-card shadow="never" class="guide">
    <template #header><b>尺寸质量评估 · 说明书</b></template>

    <el-alert type="warning" :closable="false" show-icon class="guide-alert">
      本模块使用前，请首先完成扫描点云和 BIM 离散点云的配准；具体功能参见"点云预处理"。
    </el-alert>

    <h3>模块简介</h3>
    <p>对比扫描点云和设计模型之间的偏差，进行尺寸质量评估并输出评估报告。</p>

    <h3>使用流程</h3>
    <ol>
      <li>确认已完成：离散点云、必要的下采样、单位一致性检查、扫描点云与离散点云的匹配；</li>
      <li>选择扫描点云（配准后）与 BIM 点云（配准后）；</li>
      <li>设置点云单位、偏差计算方法、平面邻域大小与剔除比例；</li>
      <li>计算偏差并生成报告：查看偏差统计指标与偏差频数直方图，并下载 PDF 报告。</li>
    </ol>

    <h3>参数说明</h3>
    <ul>
      <li><b>点云单位</b>：m / dm / cm / mm；</li>
      <li><b>偏差计算方法</b>：Point2Point（检测点到扫描点云最近点的距离）或 Point2Plane（在最近点邻域内拟合平面并计算法向距离）；</li>
      <li><b>平面邻域大小</b>：仅在 Point2Plane 时生效；</li>
      <li><b>剔除比例</b>：统计偏差指标时剔除偏差最大的点所占比例，用于降低粗差影响。</li>
    </ul>
  </el-card>
</template>

<style scoped>
.guide p,
.guide li {
  line-height: 1.9;
}
.guide-alert {
  margin-bottom: 16px;
}
</style>

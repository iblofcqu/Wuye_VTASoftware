<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <b>{{ route.meta.title ?? route.path }}</b>
    </template>
    <el-empty description="该功能页面将在后续任务中实现" />
  </el-card>
</template>

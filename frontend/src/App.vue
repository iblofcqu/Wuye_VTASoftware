<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RouterView } from 'vue-router'

import { clearSession } from '@/api/session'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
const clearing = ref(false)

async function confirmClearSession() {
  if (clearing.value) return
  try {
    await ElMessageBox.confirm(
      '确定清空当前会话的全部文件吗？此操作不可恢复。',
      '清空会话文件',
      {
        type: 'warning',
        confirmButtonText: '清空',
        cancelButtonText: '取消',
      },
    )
  } catch (reason) {
    if (reason === 'cancel' || reason === 'close') return
    ElMessage.error(reason instanceof Error ? reason.message : String(reason))
    return
  }

  clearing.value = true
  try {
    await clearSession()
    workspace.snapshot = null
    await workspace.refresh()
    ElMessage.success('删除成功')
  } catch (reason) {
    ElMessage.error(reason instanceof Error ? reason.message : String(reason))
  } finally {
    clearing.value = false
  }
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="app-aside">
      <div class="brand">
        <img src="@/assets/brand/logo.png" alt="logo" class="brand-logo" />
        <span class="brand-name">DeviScan-3D</span>
      </div>
      <el-menu router :default-active="$route.path" class="app-menu">
        <el-menu-item index="/">首页</el-menu-item>
        <el-sub-menu index="preprocess">
          <template #title>点云预处理</template>
          <el-menu-item index="/preprocess/guide">说明书</el-menu-item>
          <el-menu-item index="/preprocess/discretize">网格离散</el-menu-item>
          <el-menu-item index="/preprocess/scale">尺寸缩放</el-menu-item>
          <el-menu-item index="/preprocess/downsample">下采样</el-menu-item>
          <el-menu-item index="/preprocess/registration">配准</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="quality">
          <template #title>尺寸质量评估</template>
          <el-menu-item index="/quality/guide">说明书</el-menu-item>
          <el-menu-item index="/quality/assess">几何质量评估</el-menu-item>
        </el-sub-menu>
      </el-menu>
      <div class="app-aside-footer">
        <el-button
          class="clear-session-button"
          type="danger"
          plain
          :loading="clearing"
          :disabled="clearing"
          @click="confirmClearSession"
        >
          清空会话文件
        </el-button>
      </div>
    </el-aside>
    <el-main class="app-main">
      <RouterView />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-aside {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  background: #f7f9fb;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
}

.brand-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.brand-name {
  font-weight: 600;
  color: #4682b4;
}

.app-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  background: transparent;
}

.app-aside-footer {
  padding: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.clear-session-button {
  width: 100%;
}

.app-main {
  padding: 24px 32px;
  overflow: auto;
}
</style>

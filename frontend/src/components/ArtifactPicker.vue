<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import FileUploader from '@/components/FileUploader.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Artifact, ArtifactKind } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    kind?: ArtifactKind
    label?: string
    allowUpload?: boolean
    accept?: string
  }>(),
  {
    modelValue: null,
    kind: undefined,
    label: '',
    allowUpload: true,
    accept: undefined,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const store = useWorkspaceStore()
const showUploader = ref(false)

const options = computed(() => store.artifacts.filter((item) => !props.kind || item.kind === props.kind))

onMounted(() => {
  if (!store.snapshot) void store.refresh()
})

function onSelected(value: string) {
  emit('update:modelValue', value)
}

function onUploaded(artifact: Artifact) {
  showUploader.value = false
  void store.refresh().then(() => emit('update:modelValue', artifact.id))
}
</script>

<template>
  <div class="artifact-picker">
    <p v-if="label" class="picker-label">{{ label }}</p>
    <div class="picker-row">
      <el-select
        :model-value="modelValue"
        :placeholder="options.length ? '请选择会话产物' : '暂无可选产物'"
        class="picker-select"
        @update:model-value="onSelected"
      >
        <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-button v-if="allowUpload" link type="primary" @click="showUploader = !showUploader">
        上传新文件
      </el-button>
    </div>
    <div v-if="showUploader" class="picker-uploader">
      <FileUploader :accept="accept" @uploaded="onUploaded" />
    </div>
  </div>
</template>

<style scoped>
.picker-label {
  margin: 0 0 6px;
  font-size: 13px;
  color: #606266;
}

.picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.picker-select {
  width: 320px;
}

.picker-uploader {
  margin-top: 10px;
}
</style>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { uploadFiles } from '@/api/uploader'
import type { UploadItemState } from '@/api/uploader'
import type { Artifact } from '@/types'

const props = withDefaults(
  defineProps<{
    label?: string
    accept?: string
    multiple?: boolean
    chunkSize?: number
  }>(),
  {
    label: '选择文件上传',
    accept: '.stl,.ply,.obj,.off,.gltf,.glb,.xyz,.asc,.txt,.xls',
    multiple: true,
    chunkSize: undefined,
  },
)

const emit = defineEmits<{
  (event: 'uploaded', artifact: Artifact): void
}>()

interface Item {
  key: number
  name: string
  size: number
  status: string
  uploadedChunks: number
  totalChunks: number
  error?: string
}

const inputRef = ref<HTMLInputElement | null>(null)
const items = ref<Item[]>([])

function openPicker() {
  inputRef.value?.click()
}

function percentage(item: Item): number {
  if (item.status === 'done') return 100
  return Math.round((item.uploadedChunks / Math.max(1, item.totalChunks)) * 100)
}

function statusTag(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'done') return 'success'
  if (status === 'error') return 'danger'
  if (status === 'completing') return 'warning'
  return 'info'
}

async function onChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  target.value = ''
  if (files.length === 0) return

  const itemByFile = new Map<File, Item>()
  files.forEach((file, index) => {
    const item = reactive<Item>({
      key: Date.now() + index,
      name: file.name,
      size: file.size,
      status: 'uploading',
      uploadedChunks: 0,
      totalChunks: 0,
    })
    itemByFile.set(file, item)
    items.value.unshift(item)
  })

  const results = await uploadFiles(files, {
    chunkSize: props.chunkSize,
    onUpdate: (state: UploadItemState) => {
      const item = itemByFile.get(state.file)
      if (!item) return
      item.status = state.status
      item.uploadedChunks = state.uploadedChunks
      item.totalChunks = state.totalChunks
      item.error = state.error
    },
  })

  results.forEach((result) => {
    if (result.status === 'fulfilled' && result.value.artifact) {
      emit('uploaded', result.value.artifact)
    }
  })
}
</script>

<template>
  <div class="uploader">
    <el-button type="primary" @click="openPicker">{{ label }}</el-button>
    <input
      ref="inputRef"
      type="file"
      class="uploader-input"
      :accept="accept"
      :multiple="multiple"
      @change="onChange"
    />

    <div v-if="items.length" class="uploader-list">
      <div v-for="item in items" :key="item.key" class="uploader-item">
        <div class="uploader-line">
          <span class="uploader-name">{{ item.name }}</span>
          <el-tag :type="statusTag(item.status)" size="small">{{ item.status }}</el-tag>
        </div>
        <el-progress :percentage="percentage(item)" :status="item.status === 'error' ? 'exception' : undefined" />
        <p v-if="item.error" class="uploader-error">{{ item.error }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.uploader-input {
  display: none;
}

.uploader-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.uploader-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.uploader-name {
  font-size: 13px;
  color: #606266;
}

.uploader-error {
  color: var(--el-color-danger);
  font-size: 12px;
  margin: 4px 0 0;
}
</style>

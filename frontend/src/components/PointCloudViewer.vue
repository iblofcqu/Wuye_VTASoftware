<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import '@kitware/vtk.js/Rendering/Profiles/Geometry'
import vtkDataArray from '@kitware/vtk.js/Common/Core/DataArray'
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkColorTransferFunction from '@kitware/vtk.js/Rendering/Core/ColorTransferFunction'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkGenericRenderWindow from '@kitware/vtk.js/Rendering/Misc/GenericRenderWindow'

import type { ViewerLayer } from '@/types'
import { parseColor, seismicStops } from '@/utils/colors'
import { parseWyPv, type WyPvData } from '@/utils/wypv'

const props = withDefaults(defineProps<{ layers: ViewerLayer[]; height?: number }>(), {
  height: 360,
})

const container = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const error = ref('')

type RenderWindow = ReturnType<typeof vtkGenericRenderWindow.newInstance>
type Actor = ReturnType<typeof vtkActor.newInstance>

let renderWindow: RenderWindow | null = null
let resizeObserver: ResizeObserver | null = null
const actors: Actor[] = []

function buildActor(data: WyPvData, layer: ViewerLayer): Actor {
  const polyData = vtkPolyData.newInstance()
  polyData.getPoints().setData(data.positions, 3)

  const count = data.header.count
  const verts = new Uint32Array(count * 2)
  for (let index = 0; index < count; index += 1) {
    verts[index * 2] = 1
    verts[index * 2 + 1] = index
  }
  polyData.getVerts().setData(verts)

  const mapper = vtkMapper.newInstance()
  mapper.setInputData(polyData)

  if (data.scalars) {
    const scalars = vtkDataArray.newInstance({
      name: 'scalar',
      values: data.scalars,
      numberOfComponents: 1,
    })
    polyData.getPointData().setScalars(scalars)

    const min = data.header.scalar_min ?? 0
    const max = data.header.scalar_max ?? 1
    const transfer = vtkColorTransferFunction.newInstance()
    for (const stop of seismicStops()) {
      transfer.addRGBPoint(min + (max - min) * stop.position, stop.rgb.r, stop.rgb.g, stop.rgb.b)
    }
    mapper.setLookupTable(transfer)
    mapper.setScalarVisibility(true)
    mapper.setScalarRange(min, max)
  } else {
    mapper.setScalarVisibility(false)
  }

  const actor = vtkActor.newInstance()
  actor.setMapper(mapper)
  actor.getProperty().setPointSize(2)
  if (!data.scalars) {
    const rgb = parseColor(layer.color)
    actor.getProperty().setColor(rgb.r, rgb.g, rgb.b)
  }
  return actor
}

function clearActors() {
  if (!renderWindow) return
  const renderer = renderWindow.getRenderer()
  actors.splice(0).forEach((actor) => {
    renderer.removeActor(actor)
    actor.delete()
  })
  renderWindow.getRenderWindow().render()
}

async function loadLayers() {
  if (!renderWindow) return
  clearActors()
  error.value = ''
  if (props.layers.length === 0) return

  loading.value = true
  try {
    const renderer = renderWindow.getRenderer()
    for (const layer of props.layers) {
      const response = await fetch(layer.url, { credentials: 'same-origin' })
      if (!response.ok) throw new Error(`预览数据加载失败（${response.status}）`)
      const data = parseWyPv(await response.arrayBuffer())
      const actor = buildActor(data, layer)
      renderer.addActor(actor)
      actors.push(actor)
    }
    renderer.resetCamera()
    renderWindow.resize()
    renderWindow.getRenderWindow().render()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!container.value) return
  renderWindow = vtkGenericRenderWindow.newInstance({ background: [1, 1, 1] })
  renderWindow.setContainer(container.value)
  renderWindow.resize()
  renderWindow.getInteractor().setInteractorStyle(vtkInteractorStyleTrackballCamera.newInstance())
  renderWindow.getRenderWindow().render()

  resizeObserver = new ResizeObserver(() => {
    renderWindow?.resize()
    renderWindow?.getRenderWindow().render()
  })
  resizeObserver.observe(container.value)
  void loadLayers()
})

watch(() => props.layers, () => void loadLayers(), { deep: true })

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  clearActors()
  renderWindow?.delete()
  renderWindow = null
})
</script>

<template>
  <div class="viewer">
    <div ref="container" class="viewer-canvas" :style="{ height: `${height}px` }" />
    <div v-if="loading" class="viewer-hint">预览数据加载中…</div>
    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" class="viewer-error" />
  </div>
</template>

<style scoped>
.viewer {
  position: relative;
}

.viewer-canvas {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: #fff;
}

.viewer-hint {
  position: absolute;
  top: 8px;
  left: 12px;
  color: #909399;
  font-size: 12px;
}

.viewer-error {
  margin-top: 8px;
}
</style>

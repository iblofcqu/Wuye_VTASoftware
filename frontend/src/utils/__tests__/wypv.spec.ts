import { describe, expect, it } from 'vitest'

import { parseWyPv } from '../wypv'
import { parseColor, seismicStops } from '../colors'

function buildPreview(count: number, scalars?: number[]): ArrayBuffer {
  const header = {
    version: 1,
    count,
    source_count: count,
    decimated: false,
    fields: scalars ? ['x', 'y', 'z', 'scalar'] : ['x', 'y', 'z'],
    name: 'sample.xyz',
    ...(scalars ? { scalar_min: Math.min(...scalars), scalar_max: Math.max(...scalars), scalar_unit: 'mm', colormap: 'seismic' } : {}),
  }
  const headerBytes = new TextEncoder().encode(JSON.stringify(header))
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i += 1) positions[i] = i
  const buffers: ArrayBuffer[] = [
    new Uint8Array([0x57, 0x59, 0x50, 0x56]).buffer, // "WYPV"
    new Uint8Array([1]).buffer,
    new Uint8Array(new Uint32Array([headerBytes.length]).buffer),
    headerBytes.buffer,
    positions.buffer,
  ]
  if (scalars) buffers.push(new Float32Array(scalars).buffer)
  const total = buffers.reduce((sum, item) => sum + item.byteLength, 0)
  const merged = new Uint8Array(total)
  let offset = 0
  for (const item of buffers) {
    merged.set(new Uint8Array(item), offset)
    offset += item.byteLength
  }
  return merged.buffer
}

describe('parseWyPv', () => {
  it('解析坐标与标量', () => {
    const data = parseWyPv(buildPreview(2, [0, 5]))
    expect(data.header.count).toBe(2)
    expect(Array.from(data.positions)).toEqual([0, 1, 2, 3, 4, 5])
    expect(Array.from(data.scalars ?? [])).toEqual([0, 5])
    expect(data.header.scalar_unit).toBe('mm')
  })

  it('拒绝非法数据', () => {
    expect(() => parseWyPv(new ArrayBuffer(4))).toThrow('不完整')
    const bad = new Uint8Array([0x00, 0x00, 0x00, 0x00, 1, 0, 0, 0, 0]).buffer
    expect(() => parseWyPv(bad)).toThrow('非法')
  })
})

describe('colors', () => {
  it('解析命名色与十六进制', () => {
    expect(parseColor('blue')).toEqual({ r: 0, g: 0, b: 1 })
    expect(parseColor('#ffffff')).toEqual({ r: 1, g: 1, b: 1 })
  })

  it('seismic 色带端点为蓝/红', () => {
    const stops = seismicStops()
    expect(stops[0].rgb.b).toBeGreaterThan(0)
    expect(stops.at(-1)?.rgb.r).toBeGreaterThan(0)
  })
})

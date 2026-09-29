export interface WyPvHeader {
  version: number
  count: number
  source_count: number
  decimated?: boolean
  fields: string[]
  name?: string
  scalar_min?: number
  scalar_max?: number
  scalar_unit?: string
  colormap?: string
  zeroed_ratio?: number
}

export interface WyPvData {
  header: WyPvHeader
  positions: Float32Array
  scalars?: Float32Array
}

const MAGIC = 'WYPV'

/** 解析后端预览二进制（MAGIC + version + header_len + JSON 头 + Float32 坐标 + 可选标量）。 */
export function parseWyPv(buffer: ArrayBuffer): WyPvData {
  if (buffer.byteLength < 9) throw new Error('预览数据不完整')
  const magic = String.fromCharCode(...new Uint8Array(buffer, 0, 4))
  if (magic !== MAGIC) throw new Error('非法的预览数据')
  const view = new DataView(buffer)
  const version = view.getUint8(4)
  const headerLength = view.getUint32(5, true)
  if (buffer.byteLength < 9 + headerLength) throw new Error('预览数据不完整')

  const headerText = new TextDecoder().decode(new Uint8Array(buffer, 9, headerLength))
  const header = JSON.parse(headerText) as WyPvHeader
  if (header.version !== version) throw new Error('预览版本不一致')

  const count = header.count
  const offset = 9 + headerLength
  const positionBytes = count * 3 * 4
  if (buffer.byteLength < offset + positionBytes) throw new Error('预览坐标数据不完整')
  const positions = new Float32Array(buffer.slice(offset, offset + positionBytes))

  let scalars: Float32Array | undefined
  if (header.fields.includes('scalar')) {
    const scalarBytes = count * 4
    if (buffer.byteLength < offset + positionBytes + scalarBytes) throw new Error('预览标量数据不完整')
    scalars = new Float32Array(buffer.slice(offset + positionBytes, offset + positionBytes + scalarBytes))
  }
  return { header, positions, scalars }
}

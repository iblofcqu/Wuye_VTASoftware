export interface Rgb {
  r: number
  g: number
  b: number
}

const NAMED_COLORS: Record<string, Rgb> = {
  red: { r: 1, g: 0, b: 0 },
  blue: { r: 0, g: 0, b: 1 },
  grey: { r: 0.5, g: 0.5, b: 0.5 },
  gray: { r: 0.5, g: 0.5, b: 0.5 },
  black: { r: 0, g: 0, b: 0 },
  white: { r: 1, g: 1, b: 1 },
}

/** 支持 red/blue/grey 等命名色与 #rrggbb。 */
const FALLBACK_COLOR: Rgb = { r: 1, g: 0, b: 0 }

export function parseColor(value: string | undefined): Rgb {
  if (!value) return FALLBACK_COLOR
  const named = NAMED_COLORS[value.toLowerCase()]
  if (named) return named
  const match = /^#?([0-9a-f]{6})$/i.exec(value)
  const hex = match?.[1]
  if (hex) {
    const number = Number.parseInt(hex, 16)
    return {
      r: ((number >> 16) & 0xff) / 255,
      g: ((number >> 8) & 0xff) / 255,
      b: (number & 0xff) / 255,
    }
  }
  return FALLBACK_COLOR
}

export interface ColorStop {
  position: number
  rgb: Rgb
}

/** seismic 色带（0→蓝、0.5→白、1→红），与基线的误差色带语义一致。 */
export function seismicStops(): ColorStop[] {
  return [
    { position: 0, rgb: { r: 0, g: 0, b: 0.3 } },
    { position: 0.25, rgb: { r: 0, g: 0, b: 1 } },
    { position: 0.5, rgb: { r: 1, g: 1, b: 1 } },
    { position: 0.75, rgb: { r: 1, g: 0, b: 0 } },
    { position: 1, rgb: { r: 0.5, g: 0, b: 0 } },
  ]
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function ensureOk(response: Response): Promise<Response> {
  if (response.ok) return response
  let detail = `请求失败（${response.status}）`
  try {
    const body = await response.json()
    if (body?.detail) {
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    }
  } catch {
    // 保留默认信息
  }
  throw new ApiError(detail, response.status)
}

export async function fetchJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await ensureOk(await fetch(input, { credentials: 'same-origin', ...init }))
  return (await response.json()) as T
}

export async function sendJson<T>(input: string, method: string, payload: unknown): Promise<T> {
  return fetchJson<T>(input, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

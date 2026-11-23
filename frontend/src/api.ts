export type Approval = {
  id: string
  action_type: string
  target_id: string | null
  payload: Record<string, unknown>
  reason: string
  status: string
  created_at: string
}

export type Memory = {
  id: string
  category: string
  title: string
  content: string
  source: string
  confidence: number
  created_at: string
}

export async function api<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (init.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api${path}`, { ...init, headers })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body as T
}

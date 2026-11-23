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

type AuthResponse = {
  authenticated: boolean
  csrf_token: string
  expires_in: number
  user: { id: string; email: string; display_name: string }
}

async function responseBody<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body as T
}

export async function login(ownerToken: string): Promise<AuthResponse> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner_token: ownerToken }),
  })
  return responseBody<AuthResponse>(response)
}

export async function currentSession(): Promise<{ authenticated: boolean; user: AuthResponse['user'] }> {
  const response = await fetch('/api/auth/session', { credentials: 'include' })
  return responseBody<{ authenticated: boolean; user: AuthResponse['user'] }>(response)
}

export async function logout(csrfToken: string): Promise<{ authenticated: boolean; revoked: boolean }> {
  return api<{ authenticated: boolean; revoked: boolean }>('/auth/logout', csrfToken, { method: 'POST' })
}

export async function api<T>(path: string, csrfToken: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const method = (init.method || 'GET').toUpperCase()
  if (init.body) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRF-Token', csrfToken)
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })
  return responseBody<T>(response)
}

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

export type KnowledgeItem = {
  id: string
  knowledge_type: 'fact' | 'concept' | 'procedure' | 'skill' | 'preference' | 'principle'
  title: string
  content: string
  source_type: string
  source_ref: string | null
  confidence: number
  reinforcement_count: number
  status: 'active' | 'needs_review' | 'superseded' | 'archived'
  created_at: string
  updated_at: string
}

export type DocumentSource = {
  id: string
  title: string
  filename: string
  file_extension: string
  media_type: string
  byte_size: number
  status: 'processed' | 'needs_review' | 'archived'
  extraction_metadata: Record<string, unknown>
  created_at: string
  chunk_count: number
  embedded_chunk_count: number
}

export type KnowledgeConcept = {
  id: string
  canonical_name: string
  description: string
  source_id: string | null
}

export type KnowledgeRelation = {
  id: string
  from_concept_id: string
  from_name: string
  to_concept_id: string
  to_name: string
  relation_type: string
  evidence: string
  source_id: string | null
  confidence: number
  owner_verified: boolean
}

export type KnowledgeGraph = {
  concepts: KnowledgeConcept[]
  relations: KnowledgeRelation[]
}

export type EpisodicMemory = {
  id: string
  conversation_id: string
  content: string
  importance_score: number
  reinforcement_count: number
  recall_count: number
  last_seen_at: string
  last_recalled_at: string | null
  created_at: string
}

export type ReviewItem = {
  knowledge_id: string
  knowledge_type: string
  title: string
  content: string
  repetition_count: number
  interval_days: number
  ease_factor: number
  lapse_count: number
  last_grade: number | null
  due_at: string
  mastery_score: number
}

export type MindState = {
  architecture: string
  episodic_memories?: number
  due_reviews?: number
  average_mastery?: number
  embedding_provider?: string
  memory_system: string
  attention_system: string
  working_memory: string
  metacognition: string
  active_knowledge: number
  needs_review: number
  experiences: number
  feedback_events: number
  consciousness_claim: false
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

export async function uploadApi<T>(path: string, csrfToken: string, body: FormData): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRF-Token': csrfToken },
    body,
  })
  return responseBody<T>(response)
}

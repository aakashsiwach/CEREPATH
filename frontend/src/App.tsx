import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Activity, ArrowUpRight, BookOpen, BrainCircuit, Check, CircleAlert, Globe, KeyRound, LockKeyhole, LogOut, MessageSquare, Plus, RefreshCw, ShieldCheck, Sparkles, Trash2, X } from 'lucide-react'
import { api, currentSession, login, logout, type Approval, type Memory, type KnowledgeItem, type MindState } from './api'

type Tab = 'chat' | 'mind' | 'memory' | 'browser' | 'approvals'
type ChatMessage = { id?: string; role: 'user' | 'assistant'; content: string; provider?: string | null; model?: string | null; status?: string; created_at?: string }
type Conversation = { id: string; title: string; updated_at: string }

function App() {
  const [csrfToken, setCsrfToken] = useState(sessionStorage.getItem('cerepath_csrf_token') || '')
  const [authenticated, setAuthenticated] = useState(false)
  const [authChecking, setAuthChecking] = useState(true)
  const [tokenInput, setTokenInput] = useState('')
  const [tab, setTab] = useState<Tab>('chat')
  const [status, setStatus] = useState('Checking connection…')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const conversationsLoaded = useRef(false)
  const [message, setMessage] = useState('')
  const [memories, setMemories] = useState<Memory[]>([])
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([])
  const [mindState, setMindState] = useState<MindState | null>(null)
  const [teachTitle, setTeachTitle] = useState('')
  const [teachContent, setTeachContent] = useState('')
  const [teachType, setTeachType] = useState<KnowledgeItem['knowledge_type']>('concept')
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [memoryTitle, setMemoryTitle] = useState('')
  const [memoryContent, setMemoryContent] = useState('')
  const [browserUrl, setBrowserUrl] = useState('https://example.com')
  const [browserResult, setBrowserResult] = useState<{ title: string; final_url: string; screenshot_b64: string; warning: string } | null>(null)

  const pendingApprovals = useMemo(() => approvals.filter((item) => item.status === 'pending'), [approvals])

  const refreshData = useCallback(async () => {
    if (!authenticated || !csrfToken) return
    try {
      const [memoryData, approvalData, systemStatus, knowledgeData, cognitiveState] = await Promise.all([
        api<{ items: Memory[] }>('/memories', csrfToken),
        api<{ items: Approval[] }>('/approvals', csrfToken),
        api<{ status: string; model_calls_enabled: boolean; model_provider: string | null; model: string | null }>('/status', csrfToken),
        api<{ items: KnowledgeItem[] }>('/mind/knowledge', csrfToken),
        api<MindState>('/mind/state', csrfToken),
      ])
      setMemories(memoryData.items)
      setApprovals(approvalData.items)
      setKnowledge(knowledgeData.items)
      setMindState(cognitiveState)
      setStatus(systemStatus.model_calls_enabled ? `${systemStatus.model_provider} · ${systemStatus.model}` : 'AI provider not configured')
      setError('')
    } catch (err) {
      setStatus('Authentication or API error')
      setError(err instanceof Error ? err.message : 'Could not load workspace')
      setAuthenticated(false)
      sessionStorage.removeItem('cerepath_csrf_token')
      setCsrfToken('')
    }
  }, [authenticated, csrfToken])

  useEffect(() => {
    let active = true
    void currentSession()
      .then(() => { if (active && csrfToken) setAuthenticated(true) })
      .catch(() => { if (active) setAuthenticated(false) })
      .finally(() => { if (active) setAuthChecking(false) })
    return () => { active = false }
  }, [])

  useEffect(() => { if (authenticated) void refreshData() }, [authenticated, refreshData])

  useEffect(() => {
    if (!authenticated || !csrfToken || conversationsLoaded.current) return
    let active = true
    conversationsLoaded.current = true
    void api<{ items: Conversation[] }>('/conversations', csrfToken)
      .then((data) => {
        if (!active) return
        setConversations(data.items)
        if (data.items.length) setConversationId(data.items[0].id)
      })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'Could not load conversations') })
    return () => { active = false }
  }, [authenticated, csrfToken])

  useEffect(() => {
    if (!authenticated || !csrfToken) return
    if (!conversationId) { setMessages([]); return }
    let active = true
    void api<{ items: ChatMessage[] }>(`/conversations/${conversationId}/messages`, csrfToken)
      .then((data) => { if (active) setMessages(data.items) })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'Could not load chat history') })
    return () => { active = false }
  }, [conversationId, authenticated, csrfToken])

  async function signIn(event: FormEvent) {
    event.preventDefault()
    if (!tokenInput.trim()) return
    setBusy(true)
    try {
      const result = await login(tokenInput.trim())
      sessionStorage.setItem('cerepath_csrf_token', result.csrf_token)
      setCsrfToken(result.csrf_token)
      setAuthenticated(true)
      setTokenInput('')
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed')
    } finally { setBusy(false) }
  }

  async function signOut() {
    try { if (csrfToken) await logout(csrfToken) } catch { /* Local sign-out still clears this tab. */ }
    sessionStorage.removeItem('cerepath_csrf_token')
    setCsrfToken('')
    setAuthenticated(false)
    setMemories([])
    setApprovals([])
    setConversations([])
    setConversationId(null)
    setMessages([])
    conversationsLoaded.current = false
    setStatus('Signed out')
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    if (!message.trim() || !csrfToken) return
    const prompt = message.trim()
    setMessages((current) => [...current, { role: 'user', content: prompt }])
    setMessage('')
    setBusy(true)
    try {
      const response = await api<{ conversation_id: string; assistant_message: ChatMessage; persisted: boolean }>('/chat', csrfToken, {
        method: 'POST',
        body: JSON.stringify({ message: prompt, ...(conversationId ? { conversation_id: conversationId } : {}) }),
      })
      setConversationId(response.conversation_id)
      setMessages((current) => [...current, response.assistant_message])
      setConversations((current) => [
        { id: response.conversation_id, title: prompt.slice(0, 80), updated_at: new Date().toISOString() },
        ...current.filter((item) => item.id !== response.conversation_id),
      ])
    } catch (err) {
      setMessages((current) => [...current, { role: 'assistant', content: err instanceof Error ? err.message : 'Request failed' }])
    } finally { setBusy(false) }
  }

  async function teachCerepath(event: FormEvent) {
    event.preventDefault()
    if (!teachTitle.trim() || !teachContent.trim()) return
    setBusy(true)
    try {
      await api('/mind/teach', csrfToken, {
        method: 'POST',
        body: JSON.stringify({
          knowledge_type: teachType,
          title: teachTitle.trim(),
          content: teachContent.trim(),
        }),
      })
      setTeachTitle('')
      setTeachContent('')
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not teach Cerepath')
    } finally { setBusy(false) }
  }

  async function giveKnowledgeFeedback(id: string, outcome: 'helpful' | 'incorrect') {
    setBusy(true)
    try {
      await api('/mind/feedback', csrfToken, {
        method: 'POST',
        body: JSON.stringify({ knowledge_id: id, outcome, expected_reward: 0.5 }),
      })
      await refreshData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record learning feedback')
    } finally { setBusy(false) }
  }

  async function proposeMemory(event: FormEvent) {
    event.preventDefault()
    if (!memoryTitle.trim() || !memoryContent.trim()) return
    setBusy(true)
    try {
      await api('/approvals', csrfToken, { method: 'POST', body: JSON.stringify({
        action_type: 'memory.add', payload: { title: memoryTitle.trim(), content: memoryContent.trim(), category: 'owner-note' },
        reason: 'Owner proposed a new personal memory.',
      }) })
      setMemoryTitle(''); setMemoryContent(''); await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create proposal') }
    finally { setBusy(false) }
  }

  async function proposeUpdate(memory: Memory) {
    const title = window.prompt('Proposed new title:', memory.title)
    if (title === null) return
    const content = window.prompt('Proposed new content:', memory.content)
    if (content === null) return
    try {
      await api('/approvals', csrfToken, { method: 'POST', body: JSON.stringify({ action_type: 'memory.update', target_id: memory.id, payload: { title, content }, reason: `Owner proposed an update to memory ${memory.id}.` }) })
      await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create update proposal') }
  }

  async function proposeDelete(memory: Memory) {
    if (!window.confirm(`Create a deletion proposal for “${memory.title}”? This will NOT delete it yet.`)) return
    try {
      await api('/approvals', csrfToken, { method: 'POST', body: JSON.stringify({ action_type: 'memory.delete', target_id: memory.id, payload: {}, reason: `Owner proposed deletion of memory ${memory.id}.` }) })
      await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create deletion proposal') }
  }

  async function decide(id: string, decision: 'approve' | 'reject') {
    const item = approvals.find((entry) => entry.id === id)
    if (!item) return
    const summary = JSON.stringify({ action: item.action_type, target_id: item.target_id, payload: item.payload }, null, 2)
    if (!window.confirm(`${decision.toUpperCase()} this exact operation?\n\n${summary}`)) return
    setBusy(true)
    try {
      await api(`/approvals/${id}/decision`, csrfToken, { method: 'POST', body: JSON.stringify({ decision }) })
      await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Decision failed') }
    finally { setBusy(false) }
  }

  async function navigate(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setBrowserResult(null)
    try {
      const result = await api<typeof browserResult>('/browser/navigate', csrfToken, { method: 'POST', body: JSON.stringify({ url: browserUrl }) })
      setBrowserResult(result)
    } catch (err) { setError(err instanceof Error ? err.message : 'Browser navigation failed') }
    finally { setBusy(false) }
  }

  if (authChecking) return <main className="auth-shell"><section className="auth-card"><p className="muted">Checking your local session…</p></section></main>

  if (!authenticated) {
    return <main className="auth-shell"><section className="auth-card">
      <div className="brand-mark"><BrainCircuit size={28} /></div>
      <p className="eyebrow">PRIVATE INTELLIGENCE WORKSPACE</p>
      <h1><span>Cerepath</span></h1>
      <p className="muted">Use the local bootstrap credential once. Cerepath exchanges it for a revocable HTTP-only session; the credential is not saved in this browser.</p>
      <form onSubmit={signIn} className="stack-form">
        <label htmlFor="owner-token">Owner access token</label>
        <input id="owner-token" type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Local bootstrap credential" autoComplete="off" />
        <button className="primary-button" type="submit" disabled={busy}><KeyRound size={16}/> {busy ? 'Signing in…' : 'Unlock workspace'}</button>
      </form>
      <p className="tiny-note"><LockKeyhole size={13}/> HTTP-only session · CSRF protected · Local-only sign-in</p>
    </section></main>
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><BrainCircuit size={23}/></div><div><strong>Cerepath</strong><small>Digital twin workspace</small></div></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>
        <button className={tab === 'chat' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('chat')}><MessageSquare size={17}/> Chat</button>
        <button className={tab === 'mind' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('mind')}><BrainCircuit size={17}/> Mind</button>
        <button className={tab === 'memory' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('memory')}><BookOpen size={17}/> Memory</button>
        <button className={tab === 'browser' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('browser')}><Globe size={17}/> Browser lab</button>
        <button className={tab === 'approvals' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('approvals')}><ShieldCheck size={17}/> Approvals <span className="nav-count">{pendingApprovals.length}</span></button>
      </nav>
      <div className="sidebar-bottom"><div className="status-row"><span className="status-dot"/> Cerepath API</div><p>{status}</p><button className="subtle-button full" onClick={() => void refreshData()}><RefreshCw size={14}/> Refresh status</button><button className="subtle-button full" onClick={signOut}><LogOut size={14}/> Sign out</button></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div><p className="eyebrow">OWNER CONTROLLED SYSTEM</p><h2>{tab === 'chat' ? 'Your workspace' : tab === 'mind' ? 'Teach the digital mind' : tab === 'memory' ? 'Personal memory' : tab === 'browser' ? 'Read-only browser lab' : 'Approval centre'}</h2></div><div className="topbar-right"><span className="safe-pill"><ShieldCheck size={14}/> Approval-first mode</span><button className="icon-button" title="Sign out" onClick={signOut}><LogOut size={17}/></button></div></header>
      {error && <div className="alert"><CircleAlert size={17}/><span>{error}</span><button onClick={() => setError('')}><X size={15}/></button></div>}

      {tab === 'chat' && <section className="content chat-layout"><div className="welcome-banner"><div><p className="eyebrow">PERSONAL INTELLIGENCE · OWNER CONTROLLED</p><h3>Your context, in conversation.</h3><p>Cerepath can use recent chat history and relevant approved memories. Model calls use the provider configured by you.</p></div><Sparkles size={36}/></div><div className="chat-panel"><div className="chat-toolbar" style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}><select aria-label="Conversation history" value={conversationId || ''} onChange={(event) => setConversationId(event.target.value || null)} style={{ flex: 1, minWidth: 0 }}><option value="">New conversation</option>{conversations.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><button type="button" className="subtle-button" onClick={() => { setConversationId(null); setMessages([]) }}>New chat</button></div><div className="chat-messages">{messages.map((item, index) => <div key={`${item.role}-${index}`} className={`message ${item.role}`}><div className="message-avatar">{item.role === 'assistant' ? <BrainCircuit size={17}/> : 'A'}</div><div className="message-body"><small>{item.role === 'assistant' ? (item.provider ? `Cerepath · ${item.provider}` : 'Cerepath') : 'You'}</small><p>{item.content}</p></div></div>)}{busy && <div className="typing">Working…</div>}</div><form className="chat-composer" onSubmit={sendMessage}><textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Your command or thought…" rows={2}/><button type="submit" className="primary-button" disabled={busy || !message.trim()}><ArrowUpRight size={17}/> Send</button></form><p className="tiny-note">Conversation history is saved to your local database. Only approved memories are eligible for memory context.</p></div></section>}

      {tab === 'mind' && <section className="content two-column">
        <div className="panel">
          <div className="panel-heading"><div><h3>Teach Cerepath</h3><p>Explicit owner-taught knowledge is written to local semantic memory.</p></div><BrainCircuit size={20}/></div>
          <form className="stack-form" onSubmit={teachCerepath}>
            <label htmlFor="knowledge-type">Knowledge type</label>
            <select id="knowledge-type" value={teachType} onChange={(event) => setTeachType(event.target.value as KnowledgeItem['knowledge_type'])}>
              <option value="fact">Fact</option><option value="concept">Concept</option><option value="procedure">Procedure</option><option value="skill">Skill</option><option value="preference">Preference</option><option value="principle">Principle</option>
            </select>
            <label htmlFor="knowledge-title">Title</label>
            <input id="knowledge-title" value={teachTitle} onChange={(event) => setTeachTitle(event.target.value)} maxLength={240} placeholder="e.g. Java Collections Framework" required/>
            <label htmlFor="knowledge-content">What should Cerepath learn?</label>
            <textarea id="knowledge-content" value={teachContent} onChange={(event) => setTeachContent(event.target.value)} maxLength={20000} rows={7} placeholder="Teach a concept in your own words. Include examples and source details where possible." required/>
            <button className="primary-button" disabled={busy || !teachTitle.trim() || !teachContent.trim()}><Plus size={16}/> {busy ? 'Learning…' : 'Teach this lesson'}</button>
          </form>
          <div className="notice"><ShieldCheck size={16}/><span>This first learning milestone saves knowledge you explicitly teach. Automatic document ingestion, local embeddings, concept graphs and autonomous learning are not yet implemented.</span></div>
        </div>
        <div className="panel">
          <div className="panel-heading"><div><h3>Cognitive state</h3><p>Persistent counters from the local mind database.</p></div><Activity size={20}/></div>
          <div className="memory-list">
            <article className="memory-card"><div className="memory-meta"><span>Active knowledge</span><strong>{mindState?.active_knowledge ?? 0}</strong></div><p>Owner-taught facts, concepts, procedures, skills and principles currently available for recall.</p></article>
            <article className="memory-card"><div className="memory-meta"><span>Needs review</span><strong>{mindState?.needs_review ?? 0}</strong></div><p>Knowledge you marked incorrect and must review before it is recalled again.</p></article>
            <article className="memory-card"><div className="memory-meta"><span>Learning experiences</span><strong>{mindState?.experiences ?? 0}</strong></div><p>Lesson encoding and feedback events recorded by the system.</p></article>
          </div>
          <div className="panel-heading" style={{ marginTop: '24px' }}><div><h3>Learned knowledge</h3><p>{knowledge.length} items · newest first</p></div><BookOpen size={20}/></div>
          {knowledge.length === 0 ? <div className="empty-state">Cerepath has not been taught any lessons yet.</div> : <div className="memory-list">{knowledge.map((item) => <article className="memory-card" key={item.id}>
            <div className="memory-meta"><span>{item.knowledge_type}</span><small>{item.status} · confidence {Math.round(item.confidence * 100)}%</small></div>
            <h4>{item.title}</h4><p>{item.content}</p>
            <div className="memory-actions"><button disabled={busy} onClick={() => void giveKnowledgeFeedback(item.id, 'helpful')}><Check size={14}/> Understood correctly</button><button disabled={busy} className="danger-text" onClick={() => void giveKnowledgeFeedback(item.id, 'incorrect')}>Mark incorrect</button></div>
          </article>)}</div>}
        </div>
      </section>}

      {tab === 'memory' && <section className="content two-column"><div className="panel"><div className="panel-heading"><div><h3>Propose a memory</h3><p>Nothing is saved until you approve its proposal.</p></div><Plus size={20}/></div><form className="stack-form" onSubmit={proposeMemory}><label>Title</label><input value={memoryTitle} onChange={(e) => setMemoryTitle(e.target.value)} maxLength={240} placeholder="e.g. Preferred Java architecture" required/><label>Content</label><textarea value={memoryContent} onChange={(e) => setMemoryContent(e.target.value)} maxLength={20000} rows={6} placeholder="Write the information you want your clone to remember…" required/><button className="primary-button" disabled={busy}><ShieldCheck size={16}/> Request approval</button></form></div><div className="panel"><div className="panel-heading"><div><h3>Approved memories</h3><p>{memories.length} saved items</p></div><BookOpen size={20}/></div>{memories.length === 0 ? <div className="empty-state">No approved memories yet.</div> : <div className="memory-list">{memories.map((item) => <article className="memory-card" key={item.id}><div className="memory-meta"><span>{item.category}</span><small>{new Date(item.created_at).toLocaleDateString()}</small></div><h4>{item.title}</h4><p>{item.content}</p><div className="memory-actions"><button onClick={() => void proposeUpdate(item)}>Propose update</button><button className="danger-text" onClick={() => void proposeDelete(item)}><Trash2 size={14}/> Propose delete</button></div></article>)}</div>}</div></section>}

      {tab === 'browser' && <section className="content"><div className="panel browser-panel"><div className="panel-heading"><div><h3>Public web inspection</h3><p>Disposable browser session · GET-only · no saved cookies</p></div><Globe size={21}/></div><form className="browser-form" onSubmit={navigate}><input type="url" value={browserUrl} onChange={(e) => setBrowserUrl(e.target.value)} placeholder="https://example.com" required/><button className="primary-button" disabled={busy}><Globe size={16}/> {busy ? 'Loading…' : 'Open and inspect'}</button></form><div className="notice"><LockKeyhole size={16}/><span>This first milestone cannot click, type, submit forms or sign into websites. Only public HTTPS pages and GET requests are allowed.</span></div>{browserResult && <div className="browser-result"><div className="result-heading"><div><strong>{browserResult.title || 'Untitled page'}</strong><a href={browserResult.final_url} target="_blank" rel="noreferrer">{browserResult.final_url} <ArrowUpRight size={12}/></a></div><span className="safe-pill">Read only</span></div><img src={`data:image/jpeg;base64,${browserResult.screenshot_b64}`} alt="Browser screenshot"/><p className="tiny-note">{browserResult.warning}</p></div>}</div></section>}

      {tab === 'approvals' && <section className="content"><div className="panel"><div className="panel-heading"><div><h3>Pending owner decisions</h3><p>Review the exact operation and payload before approval.</p></div><ShieldCheck size={21}/></div>{pendingApprovals.length === 0 ? <div className="empty-state"><Check size={22}/><strong>No pending approvals</strong><span>Any proposed memory change will appear here.</span></div> : <div className="approval-list">{pendingApprovals.map((item) => <article className="approval-card" key={item.id}><div className="approval-heading"><span className="pending-tag">Pending</span><small>{new Date(item.created_at).toLocaleString()}</small></div><h4>{item.action_type}</h4><p>{item.reason}</p><pre>{JSON.stringify({ target_id: item.target_id, payload: item.payload }, null, 2)}</pre><div className="approval-actions"><button className="reject-button" disabled={busy} onClick={() => void decide(item.id, 'reject')}><X size={15}/> Reject</button><button className="primary-button" disabled={busy} onClick={() => void decide(item.id, 'approve')}><Check size={15}/> Approve this exact change</button></div></article>)}</div>}</div></section>}
      <footer className="footer"><span><Activity size={13}/> Cerepath workspace v0.4.0</span><span>{status} · Memory changes require your approval</span></footer>
    </main>
  </div>
}

export default App

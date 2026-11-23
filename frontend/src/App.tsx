import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Activity, ArrowUpRight, BookOpen, BrainCircuit, Check, CircleAlert, Globe, KeyRound, LockKeyhole, LogOut, MessageSquare, Plus, RefreshCw, ShieldCheck, Sparkles, Trash2, X } from 'lucide-react'
import { api, type Approval, type Memory } from './api'

type Tab = 'chat' | 'memory' | 'browser' | 'approvals'
type ChatMessage = { role: 'user' | 'assistant'; content: string }

const initialMessages: ChatMessage[] = [{ role: 'assistant', content: 'Welcome to Cerepath. The secure local foundation is running. The reasoning model is not connected yet, and this chat does not save your messages or call an external AI service.' }]

function App() {
  const [token, setToken] = useState(sessionStorage.getItem('cerepath_owner_token') || '')
  const [tokenInput, setTokenInput] = useState('')
  const [tab, setTab] = useState<Tab>('chat')
  const [status, setStatus] = useState('Checking connection…')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [message, setMessage] = useState('')
  const [memories, setMemories] = useState<Memory[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [memoryTitle, setMemoryTitle] = useState('')
  const [memoryContent, setMemoryContent] = useState('')
  const [browserUrl, setBrowserUrl] = useState('https://example.com')
  const [browserResult, setBrowserResult] = useState<{ title: string; final_url: string; screenshot_b64: string; warning: string } | null>(null)

  const authenticated = Boolean(token)
  const pendingApprovals = useMemo(() => approvals.filter((item) => item.status === 'pending'), [approvals])

  const refreshData = useCallback(async () => {
    if (!token) return
    try {
      const [memoryData, approvalData, systemStatus] = await Promise.all([
        api<{ items: Memory[] }>('/memories', token),
        api<{ items: Approval[] }>('/approvals', token),
        api<{ status: string; external_model_calls_enabled: boolean }>('/status', token),
      ])
      setMemories(memoryData.items)
      setApprovals(approvalData.items)
      setStatus(systemStatus.external_model_calls_enabled ? 'Connected' : 'Local foundation · no AI provider')
      setError('')
    } catch (err) {
      setStatus('Authentication or API error')
      setError(err instanceof Error ? err.message : 'Could not load workspace')
    }
  }, [token])

  useEffect(() => { void refreshData() }, [refreshData])

  function signIn(event: FormEvent) {
    event.preventDefault()
    if (!tokenInput.trim()) return
    sessionStorage.setItem('cerepath_owner_token', tokenInput.trim())
    setToken(tokenInput.trim())
    setTokenInput('')
  }

  function signOut() {
    sessionStorage.removeItem('cerepath_owner_token')
    setToken('')
    setMemories([])
    setApprovals([])
    setStatus('Signed out')
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    if (!message.trim() || !token) return
    const prompt = message.trim()
    setMessages((current) => [...current, { role: 'user', content: prompt }])
    setMessage('')
    setBusy(true)
    try {
      const response = await api<{ content: string }>('/chat', token, { method: 'POST', body: JSON.stringify({ message: prompt }) })
      setMessages((current) => [...current, { role: 'assistant', content: response.content }])
    } catch (err) {
      setMessages((current) => [...current, { role: 'assistant', content: err instanceof Error ? err.message : 'Request failed' }])
    } finally { setBusy(false) }
  }

  async function proposeMemory(event: FormEvent) {
    event.preventDefault()
    if (!memoryTitle.trim() || !memoryContent.trim()) return
    setBusy(true)
    try {
      await api('/approvals', token, { method: 'POST', body: JSON.stringify({
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
      await api('/approvals', token, { method: 'POST', body: JSON.stringify({ action_type: 'memory.update', target_id: memory.id, payload: { title, content }, reason: `Owner proposed an update to memory ${memory.id}.` }) })
      await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create update proposal') }
  }

  async function proposeDelete(memory: Memory) {
    if (!window.confirm(`Create a deletion proposal for “${memory.title}”? This will NOT delete it yet.`)) return
    try {
      await api('/approvals', token, { method: 'POST', body: JSON.stringify({ action_type: 'memory.delete', target_id: memory.id, payload: {}, reason: `Owner proposed deletion of memory ${memory.id}.` }) })
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
      await api(`/approvals/${id}/decision`, token, { method: 'POST', body: JSON.stringify({ decision }) })
      await refreshData()
    } catch (err) { setError(err instanceof Error ? err.message : 'Decision failed') }
    finally { setBusy(false) }
  }

  async function navigate(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setBrowserResult(null)
    try {
      const result = await api<typeof browserResult>('/browser/navigate', token, { method: 'POST', body: JSON.stringify({ url: browserUrl }) })
      setBrowserResult(result)
    } catch (err) { setError(err instanceof Error ? err.message : 'Browser navigation failed') }
    finally { setBusy(false) }
  }

  if (!authenticated) {
    return <main className="auth-shell"><section className="auth-card">
      <div className="brand-mark"><BrainCircuit size={28} /></div>
      <p className="eyebrow">PRIVATE INTELLIGENCE WORKSPACE</p>
      <h1><span>Cerepath</span></h1>
      <p className="muted">Sign in to your local starter workspace. Your owner token stays in this browser tab only.</p>
      <form onSubmit={signIn} className="stack-form">
        <label htmlFor="owner-token">Owner access token</label>
        <input id="owner-token" type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Paste CEREPATH_OWNER_TOKEN" autoComplete="off" />
        <button className="primary-button" type="submit"><KeyRound size={16}/> Unlock workspace</button>
      </form>
      <p className="tiny-note"><LockKeyhole size={13}/> Local-only starter · No external AI calls</p>
    </section></main>
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><BrainCircuit size={23}/></div><div><strong>Cerepath</strong><small>Digital twin workspace</small></div></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>
        <button className={tab === 'chat' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('chat')}><MessageSquare size={17}/> Chat</button>
        <button className={tab === 'memory' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('memory')}><BookOpen size={17}/> Memory</button>
        <button className={tab === 'browser' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('browser')}><Globe size={17}/> Browser lab</button>
        <button className={tab === 'approvals' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('approvals')}><ShieldCheck size={17}/> Approvals <span className="nav-count">{pendingApprovals.length}</span></button>
      </nav>
      <div className="sidebar-bottom"><div className="status-row"><span className="status-dot"/> Cerepath API</div><p>{status}</p><button className="subtle-button full" onClick={() => void refreshData()}><RefreshCw size={14}/> Refresh status</button><button className="subtle-button full" onClick={signOut}><LogOut size={14}/> Sign out</button></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div><p className="eyebrow">OWNER CONTROLLED SYSTEM</p><h2>{tab === 'chat' ? 'Your workspace' : tab === 'memory' ? 'Personal memory' : tab === 'browser' ? 'Read-only browser lab' : 'Approval centre'}</h2></div><div className="topbar-right"><span className="safe-pill"><ShieldCheck size={14}/> Approval-first mode</span><button className="icon-button" title="Sign out" onClick={signOut}><LogOut size={17}/></button></div></header>
      {error && <div className="alert"><CircleAlert size={17}/><span>{error}</span><button onClick={() => setError('')}><X size={15}/></button></div>}

      {tab === 'chat' && <section className="content chat-layout"><div className="welcome-banner"><div><p className="eyebrow">MILESTONE 0 · FOUNDATION</p><h3>Build beyond what you know.</h3><p>The secure workspace is here. Intelligence providers remain disconnected until the model and privacy policy are designed.</p></div><Sparkles size={36}/></div><div className="chat-panel"><div className="chat-messages">{messages.map((item, index) => <div key={`${item.role}-${index}`} className={`message ${item.role}`}><div className="message-avatar">{item.role === 'assistant' ? <BrainCircuit size={17}/> : 'A'}</div><div className="message-body"><small>{item.role === 'assistant' ? 'Cerepath' : 'You'}</small><p>{item.content}</p></div></div>)}{busy && <div className="typing">Working…</div>}</div><form className="chat-composer" onSubmit={sendMessage}><textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Your command or thought…" rows={2}/><button type="submit" className="primary-button" disabled={busy || !message.trim()}><ArrowUpRight size={17}/> Send</button></form><p className="tiny-note">Chat is ephemeral in this milestone. Messages are not saved as memories.</p></div></section>}

      {tab === 'memory' && <section className="content two-column"><div className="panel"><div className="panel-heading"><div><h3>Propose a memory</h3><p>Nothing is saved until you approve its proposal.</p></div><Plus size={20}/></div><form className="stack-form" onSubmit={proposeMemory}><label>Title</label><input value={memoryTitle} onChange={(e) => setMemoryTitle(e.target.value)} maxLength={240} placeholder="e.g. Preferred Java architecture" required/><label>Content</label><textarea value={memoryContent} onChange={(e) => setMemoryContent(e.target.value)} maxLength={20000} rows={6} placeholder="Write the information you want your clone to remember…" required/><button className="primary-button" disabled={busy}><ShieldCheck size={16}/> Request approval</button></form></div><div className="panel"><div className="panel-heading"><div><h3>Approved memories</h3><p>{memories.length} saved items</p></div><BookOpen size={20}/></div>{memories.length === 0 ? <div className="empty-state">No approved memories yet.</div> : <div className="memory-list">{memories.map((item) => <article className="memory-card" key={item.id}><div className="memory-meta"><span>{item.category}</span><small>{new Date(item.created_at).toLocaleDateString()}</small></div><h4>{item.title}</h4><p>{item.content}</p><div className="memory-actions"><button onClick={() => void proposeUpdate(item)}>Propose update</button><button className="danger-text" onClick={() => void proposeDelete(item)}><Trash2 size={14}/> Propose delete</button></div></article>)}</div>}</div></section>}

      {tab === 'browser' && <section className="content"><div className="panel browser-panel"><div className="panel-heading"><div><h3>Public web inspection</h3><p>Disposable browser session · GET-only · no saved cookies</p></div><Globe size={21}/></div><form className="browser-form" onSubmit={navigate}><input type="url" value={browserUrl} onChange={(e) => setBrowserUrl(e.target.value)} placeholder="https://example.com" required/><button className="primary-button" disabled={busy}><Globe size={16}/> {busy ? 'Loading…' : 'Open and inspect'}</button></form><div className="notice"><LockKeyhole size={16}/><span>This first milestone cannot click, type, submit forms or sign into websites. Only public HTTPS pages and GET requests are allowed.</span></div>{browserResult && <div className="browser-result"><div className="result-heading"><div><strong>{browserResult.title || 'Untitled page'}</strong><a href={browserResult.final_url} target="_blank" rel="noreferrer">{browserResult.final_url} <ArrowUpRight size={12}/></a></div><span className="safe-pill">Read only</span></div><img src={`data:image/jpeg;base64,${browserResult.screenshot_b64}`} alt="Browser screenshot"/><p className="tiny-note">{browserResult.warning}</p></div>}</div></section>}

      {tab === 'approvals' && <section className="content"><div className="panel"><div className="panel-heading"><div><h3>Pending owner decisions</h3><p>Review the exact operation and payload before approval.</p></div><ShieldCheck size={21}/></div>{pendingApprovals.length === 0 ? <div className="empty-state"><Check size={22}/><strong>No pending approvals</strong><span>Any proposed memory change will appear here.</span></div> : <div className="approval-list">{pendingApprovals.map((item) => <article className="approval-card" key={item.id}><div className="approval-heading"><span className="pending-tag">Pending</span><small>{new Date(item.created_at).toLocaleString()}</small></div><h4>{item.action_type}</h4><p>{item.reason}</p><pre>{JSON.stringify({ target_id: item.target_id, payload: item.payload }, null, 2)}</pre><div className="approval-actions"><button className="reject-button" disabled={busy} onClick={() => void decide(item.id, 'reject')}><X size={15}/> Reject</button><button className="primary-button" disabled={busy} onClick={() => void decide(item.id, 'approve')}><Check size={15}/> Approve this exact change</button></div></article>)}</div>}</div></section>}
      <footer className="footer"><span><Activity size={13}/> Cerepath foundation v0.2.0</span><span>External AI: disabled · Paid services: none · Cloud provisioning: none</span></footer>
    </main>
  </div>
}

export default App

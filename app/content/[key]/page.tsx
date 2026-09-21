import Link from 'next/link'
import { notFound, redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/auth'
import { getItem, attachSeeds, writers as getWriters, approveAndAllocate, rejectDraft, submitRewrite, requestRewrite, completeItem, cancelItem } from '@/lib/store'
import { STAGES, ACTION_LABEL, TERMINAL, canApprove, canWrite, isAdmin } from '@/lib/types'

function tone(stage: string) {
  for (const [, s] of Object.entries(STAGES)) if (s.actions.includes(stage as never)) return s.tone
  if (['REJECTED','DELETED'].includes(stage)) return 'danger'
  return 'neutral'
}
function fmtDT(iso?: string) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }
  catch { return iso }
}
function ago(iso?: string) {
  if (!iso) return '—'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 90) return 'just now'
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return `${Math.floor(s/86400)}d ago`
}

export default async function ContentPage({
  params, searchParams,
}: {
  params: { key: string }
  searchParams: { flash?: string; tone?: string; err?: string }
}) {
  const uniqueKey = decodeURIComponent(params.key)
  const user = await getCurrentUser()
  if (!user) redirect('/')

  const items = await attachSeeds([await getItem(uniqueKey) ?? notFound()])
  const item = items[0]
  const seed = item.seed

  const approverView = canApprove(user)
  const writerView   = canWrite(user) && item.assigneeUserId === user.id

  const writersForApprove = approverView && item.stage === 'DRAFT_RECEIVED'
    ? await getWriters() : []

  // ---- Server Actions -----------------------------------------------

  async function doApprove(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !canApprove(actor)) return
    const assigneeId = Number(fd.get('assignee_user_id'))
    const comment    = String(fd.get('comment') ?? '')
    const { writers: getWritersFn } = await import('@/lib/store')
    const all = await getWritersFn()
    const assignee = all.find(w => w.id === assigneeId)
    if (!assignee) { redirect(`/content/${uniqueKey}?err=Pick+a+writer`) }
    try {
      await approveAndAllocate(uniqueKey, actor, assignee, comment || undefined)
      redirect(`/content/${uniqueKey}?flash=Approved+%26+allocated+to+${encodeURIComponent(assignee.username)}&tone=good`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  async function doReject(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !canApprove(actor)) return
    try {
      await rejectDraft(uniqueKey, actor, String(fd.get('comment') ?? '') || undefined)
      redirect(`/content/${uniqueKey}?flash=Rejected.+Request+is+closed.&tone=warn`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  async function doSubmit(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor) return
    try {
      await submitRewrite(uniqueKey, actor, String(fd.get('content_text') ?? ''), String(fd.get('content_url') ?? ''), String(fd.get('comment') ?? '') || undefined)
      redirect(`/content/${uniqueKey}?flash=Submitted+for+review&tone=good`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  async function doRewrite(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !canApprove(actor)) return
    try {
      await requestRewrite(uniqueKey, actor, String(fd.get('comment') ?? ''))
      redirect(`/content/${uniqueKey}?flash=Sent+back+for+rewrite&tone=warn`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  async function doComplete(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !canApprove(actor)) return
    try {
      await completeItem(uniqueKey, actor, String(fd.get('comment') ?? '') || undefined)
      redirect(`/content/${uniqueKey}?flash=Completed+%F0%9F%8E%89&tone=good`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  async function doCancel(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !isAdmin(actor)) return
    try {
      await cancelItem(uniqueKey, actor, String(fd.get('comment') ?? '') || undefined)
      redirect(`/content/${uniqueKey}?flash=Request+cancelled.&tone=warn`)
    } catch (e: unknown) { redirect(`/content/${uniqueKey}?err=${encodeURIComponent(String((e as Error).message))}`) }
  }

  const isTerminal = TERMINAL.includes(item.stage as never)
  const stageNum = item.stage === 'DRAFT_RECEIVED' ? 2 : item.stage === 'ALLOCATED' || item.stage === 'REWRITE_REQUESTED' ? 3 : item.stage === 'SUBMITTED' ? 4 : item.stage === 'COMPLETED' ? 5 : 0

  return (
    <>
      <div className="page-top">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href={stageNum > 0 ? `/stage/${stageNum}` : '/dashboard'} className="btn quiet" style={{ padding: '6px 10px', fontSize: 13 }}>← Back</Link>
          <div>
            <h1 style={{ fontSize: 16, margin: 0 }}>{seed?.gemstoneName || uniqueKey}</h1>
            <div className="page-top-sub">{uniqueKey}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className={`badge big ${tone(item.stage)}`}>{ACTION_LABEL[item.stage as keyof typeof ACTION_LABEL]}</span>
          {(item.contentUrl || seed?.aiDraftUrl) && (
            <a className="btn" href={item.contentUrl || seed?.aiDraftUrl || '#'} target="_blank" rel="noopener">Open doc ↗</a>
          )}
        </div>
      </div>

      <main>
        <div className="wrap narrow">
          {searchParams.flash && <div className={`flash ${searchParams.tone ?? 'good'}`} style={{ marginBottom: 14 }}>{decodeURIComponent(searchParams.flash)}</div>}
          {searchParams.err && <div className="flash danger" style={{ marginBottom: 14 }}>{decodeURIComponent(searchParams.err)}</div>}

          {/* Rewrite note */}
          {item.stage === 'REWRITE_REQUESTED' && item.lastComment && (
            <div className="notice" style={{ marginBottom: 16 }}>
              <b>Sent back for changes.</b> {item.lastComment}
            </div>
          )}
          {item.stage === 'REJECTED' && (
            <div className="notice" style={{ marginBottom: 16 }}>
              <b>Rejected.</b> {item.lastComment || 'No reason recorded.'} This request is permanently closed.
            </div>
          )}
          {item.stage === 'DELETED' && (
            <div className="notice calm" style={{ marginBottom: 16 }}>
              <b>Cancelled.</b> {item.lastComment || 'No reason recorded.'}
            </div>
          )}

          {/* Meta */}
          <div className="card sunk">
            <dl className="facts">
              <dt>Writer</dt>
              <dd>{item.assigneeEmail ? <b>{item.assigneeEmail}</b> : <span style={{color:'var(--muted)'}}>Not allocated yet</span>}</dd>
              <dt>Revision</dt>
              <dd>{item.revisionNumber}{item.revisionNumber === 0 ? <span className="src"> · AI draft, untouched</span> : null}</dd>
              <dt>Words</dt>
              <dd>{item.wordCount ?? (item.contentText ? item.contentText.split(/\s+/).length : null) ?? '—'}</dd>
              <dt>Created</dt>
              <dd>{fmtDT(item.createdAt)}</dd>
              <dt>Last change</dt>
              <dd>{fmtDT(item.updatedAt)} <span className="src">· {ago(item.updatedAt)}</span></dd>
            </dl>
          </div>

          {/* Brief from AI_Content_Queue */}
          {seed && (
            <>
              <div className="eyebrow" style={{ margin: '20px 0 10px' }}>
                Stage 1 Brief <span style={{ textTransform: 'none', letterSpacing: 0, fontWeight: 400, fontSize: 11.5 }}>· from AI_Content_Queue, read-only</span>
              </div>
              <div className="card">
                <div className="kpis">
                  {seed.searchVolume && <span className="kpi"><b>{seed.searchVolume.toLocaleString('en-IN')}</b> monthly searches</span>}
                  {seed.keywordDifficulty && <span className="kpi">difficulty <b>{seed.keywordDifficulty}</b>/100</span>}
                  {seed.intent && <span className="kpi">{seed.intent}</span>}
                  {seed.contentType && <span className="kpi">{seed.contentType}</span>}
                  {seed.priority && <span className="kpi">{seed.priority} priority</span>}
                  {seed.aiConfidence != null && <span className="kpi">AI confidence <b>{seed.aiConfidence.toFixed(2)}</b></span>}
                </div>
                <dl className="facts">
                  <dt>Search term <span className="src">· auto</span></dt>
                  <dd><b>{seed.searchTerm || '—'}</b></dd>
                  {seed.secondaryKeywords && <><dt>Also targeting <span className="src">· auto</span></dt><dd>{seed.secondaryKeywords}</dd></>}
                  <dt>Target page <span className="src">· auto</span></dt>
                  <dd>{seed.targetUrl ? <a className="mono" href={seed.targetUrl} target="_blank" rel="noopener">{seed.targetUrl}</a> : 'New page'}</dd>
                  {seed.metaTitle && <><dt>Meta title <span className="src">· auto</span></dt><dd>{seed.metaTitle}</dd></>}
                  {seed.metaDescription && <><dt>Meta description <span className="src">· auto</span></dt><dd>{seed.metaDescription}</dd></>}
                  {seed.researchNotes && <><dt>Why this one <span className="src">· auto</span></dt><dd>{seed.researchNotes}</dd></>}
                  {seed.aiModel && <><dt>AI model <span className="src">· auto</span></dt><dd>{seed.aiModel}</dd></>}
                  {seed.plannedDate && <><dt>Planned date</dt><dd>{seed.plannedDate}</dd></>}
                </dl>
              </div>
            </>
          )}

          {/* The content */}
          <div className="eyebrow" style={{ margin: '20px 0 10px' }}>
            {item.revisionNumber ? `Revision ${item.revisionNumber}` : 'AI Draft'}
          </div>
          <div className="card">
            {item.contentUrl && <p className="mono" style={{ marginBottom: 12 }}><a href={item.contentUrl} target="_blank" rel="noopener">{item.contentUrl}</a></p>}
            {item.contentText
              ? <div className="body-text">{item.contentText}</div>
              : <p style={{ color: 'var(--muted)', margin: 0 }}>No content text yet.</p>
            }
          </div>

          {/* ---- STAGE 2: Vivek decides on AI draft ---- */}
          {item.stage === 'DRAFT_RECEIVED' && approverView && (
            <>
              <div className="eyebrow" style={{ margin: '24px 0 10px' }}>Stage 2 · Your decision</div>
              <div className="card">
                <h2>Approve and send to Kirti</h2>
                <p>Approving allocates it in one step — it never sits without a writer.</p>
                <form action={doApprove} className="stack">
                  <div>
                    <label className="lab" htmlFor="assignee">Writer</label>
                    <select className="field" name="assignee_user_id" id="assignee" required>
                      <option value="" disabled>Choose a writer</option>
                      {writersForApprove.map(w => (
                        <option key={w.id} value={w.id}>{w.username} — {w.email}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="lab" htmlFor="approve_comment">Brief for Kirti <span className="hint">· optional</span></label>
                    <textarea className="field" name="comment" id="approve_comment" rows={2} placeholder="Anything they should change or watch for" />
                  </div>
                  <button className="btn primary" type="submit">Approve and allocate to Kirti</button>
                </form>
              </div>
              <div className="card">
                <h2 style={{ color: 'var(--danger-ink)' }}>Reject AI draft</h2>
                <p>Permanently closes this request. The AI brief stays in AI_Content_Queue for reference.</p>
                <form action={doReject} className="stack" onSubmit="return confirm('Reject this AI draft? The request closes permanently.')">
                  <textarea className="field" name="comment" rows={2} placeholder="Why it's being rejected" />
                  <button className="btn danger" type="submit">Reject and close</button>
                </form>
              </div>
            </>
          )}

          {/* ---- STAGE 3: Kirti writes ---- */}
          {['ALLOCATED','REWRITE_REQUESTED'].includes(item.stage) && writerView && (
            <>
              <div className="eyebrow" style={{ margin: '24px 0 10px' }}>Stage 3 · Your turn</div>
              <div className="card">
                <h2>Submit your rewrite</h2>
                <p>This goes to Stage 4 where Vivek reviews it as revision {(item.revisionNumber ?? 0) + 1}.</p>
                <form action={doSubmit} className="stack">
                  <div>
                    <label className="lab" htmlFor="content_text">Content</label>
                    <textarea className="field" name="content_text" id="content_text" rows={14} defaultValue={item.contentText ?? ''} />
                  </div>
                  <div>
                    <label className="lab" htmlFor="content_url">Google Doc link <span className="hint">· if you prefer to link instead</span></label>
                    <input className="field mono" type="url" name="content_url" id="content_url" defaultValue={item.contentUrl ?? ''} placeholder="https://docs.google.com/…" />
                  </div>
                  <div>
                    <label className="lab" htmlFor="submit_comment">Note for Vivek <span className="hint">· optional</span></label>
                    <textarea className="field" name="comment" id="submit_comment" rows={2} placeholder="What you changed" />
                  </div>
                  <button className="btn primary" type="submit">Submit for Vivek's review</button>
                </form>
              </div>
            </>
          )}
          {['ALLOCATED','REWRITE_REQUESTED'].includes(item.stage) && !writerView && (
            <div className="notice calm" style={{ marginTop: 16 }}>
              Allocated to {item.assigneeEmail || 'a writer'}. Waiting on their rewrite.
            </div>
          )}

          {/* ---- STAGE 4: Vivek reviews Kirti's version ---- */}
          {item.stage === 'SUBMITTED' && approverView && (
            <>
              <div className="eyebrow" style={{ margin: '24px 0 10px' }}>Stage 4 · Your decision</div>
              <div className="card">
                <h2>Approve and complete</h2>
                <p>Revision {item.revisionNumber} becomes the final copy. This closes the loop.</p>
                <form action={doComplete} className="stack">
                  <textarea className="field" name="comment" rows={2} placeholder="Closing note (optional)" />
                  <button className="btn primary" type="submit">Approve — mark completed</button>
                </form>
              </div>
              <div className="card">
                <h2>Send back to Kirti</h2>
                <p>Goes back to Stage 3 with your notes. Kirti resubmits and it comes to you again.</p>
                <form action={doRewrite} className="stack">
                  <textarea className="field" name="comment" rows={3} required placeholder="What specifically needs to change" />
                  <button className="btn" type="submit">Send back for rewrite</button>
                </form>
              </div>
            </>
          )}

          {/* Admin cancel */}
          {isAdmin(user) && !isTerminal && (
            <div className="card" style={{ marginTop: 14 }}>
              <h2 style={{ color: 'var(--danger-ink)' }}>Cancel this request</h2>
              <p>Admin only. Permanently removes it from the active workflow.</p>
              <form action={doCancel} className="stack">
                <textarea className="field" name="comment" rows={2} placeholder="Reason (optional)" />
                <button className="btn danger" type="submit">Cancel request</button>
              </form>
            </div>
          )}

          {/* History */}
          <div className="eyebrow" style={{ margin: '26px 0 10px' }}>History</div>
          <div className="card">
            <ol className="trail">
              {[...item.history].reverse().map((ev, idx) => (
                <li key={ev.eventId} className={idx === 0 ? 'now' : ''}>
                  <div className="tw">
                    {ACTION_LABEL[ev.action as keyof typeof ACTION_LABEL] ?? ev.action}
                    <span className="tt"> · {fmtDT(ev.timestamp)}</span>
                  </div>
                  <div className="tb">{ev.actorEmail || 'Automated'}</div>
                  {ev.action === 'ALLOCATED' && ev.assigneeEmail && <div className="tb">Allocated to {ev.assigneeEmail}</div>}
                  {ev.comment && <div className="tn">{ev.comment}</div>}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </main>
    </>
  )
}

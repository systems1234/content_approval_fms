import Link from 'next/link'
import { getCurrentUser } from '@/lib/auth'
import { listItems, pendingSeeds, counts, attachSeeds, syncAIDrafts } from '@/lib/store'
import { STAGES, ACTION_LABEL, TERMINAL, canApprove, isAdmin } from '@/lib/types'
import { redirect } from 'next/navigation'

function tone(stage: string) {
  for (const [, s] of Object.entries(STAGES)) if (s.actions.includes(stage as never)) return s.tone
  if (['REJECTED','DELETED'].includes(stage)) return 'danger'
  return 'neutral'
}

function ago(iso?: string) {
  if (!iso) return '—'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 90) return 'just now'
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  if (s < 604800) return `${Math.floor(s/86400)}d ago`
  return `${Math.floor(s/604800)}w ago`
}

async function SyncAction() {
  'use server'
  const user = await getCurrentUser()
  if (!user || !canApprove(user)) return
  await syncAIDrafts()
  redirect('/stage/2')
}

export default async function Dashboard({ searchParams }: { searchParams: { flash?: string; tone?: string } }) {
  const user = await getCurrentUser()
  if (!user) redirect('/')

  const [allItems, pending, c] = await Promise.all([listItems(), pendingSeeds(), counts(user)])
  const withSeeds = await attachSeeds(allItems.slice(0, 20))
  const mine = withSeeds.filter(i => {
    if (TERMINAL.includes(i.stage as never)) return false
    if (canApprove(user) && ['DRAFT_RECEIVED','SUBMITTED'].includes(i.stage)) return true
    if (['ALLOCATED','REWRITE_REQUESTED'].includes(i.stage) && i.assigneeUserId === user.id) return true
    return false
  }).slice(0, 8)
  const recent = withSeeds.slice(0, 8)

  return (
    <>
      <div className="page-top">
        <div>
          <h1>Overview</h1>
          <div className="page-top-sub">Content FMS · mis-gempundit</div>
        </div>
        {canApprove(user) && (
          <form action={SyncAction}>
            <button className={`btn${c.stage1 > 0 ? ' primary' : ''}`} type="submit">
              {c.stage1 > 0 ? `Pull in ${c.stage1} new draft${c.stage1 === 1 ? '' : 's'}` : 'No new drafts'}
            </button>
          </form>
        )}
      </div>

      <main>
        <div className="wrap">
          {searchParams.flash && (
            <div className={`flash ${searchParams.tone ?? 'good'}`} style={{ marginBottom: 14 }}>{searchParams.flash}</div>
          )}

          <div className="stats" style={{ marginBottom: 24 }}>
            <Link href="/stage/1" className={`stat${c.stage1 > 0 ? ' live' : ' zero'}`}>
              <div className="n">{c.stage1}</div>
              <div className="k">Stage 1 · AI Content</div>
            </Link>
            <Link href="/stage/2" className={`stat${c.stage2 > 0 ? ' live' : ' zero'}`}>
              <div className="n">{c.stage2}</div>
              <div className="k">Stage 2 · Vivek Approval</div>
            </Link>
            <Link href="/stage/3" className={`stat${c.stage3 > 0 ? ' live' : ' zero'}`}>
              <div className="n">{c.stage3}</div>
              <div className="k">Stage 3 · Kirti Writing</div>
            </Link>
            <Link href="/stage/4" className={`stat${c.stage4 > 0 ? ' live' : ' zero'}`}>
              <div className="n">{c.stage4}</div>
              <div className="k">Stage 4 · Vivek Review</div>
            </Link>
            <Link href="/stage/5" className={`stat${c.stage5 > 0 ? ' live' : ' zero'}`}>
              <div className="n">{c.stage5}</div>
              <div className="k">Stage 5 · Completed</div>
            </Link>
          </div>

          <div className="eyebrow" style={{ marginBottom: 10 }}>On your desk</div>
          {mine.length ? (
            <div className="table" style={{ '--cols': 'minmax(0,1.6fr) minmax(0,1fr) 170px 110px' } as React.CSSProperties}>
              {mine.map(item => (
                <Link key={item.uniqueKey} href={`/content/${item.uniqueKey}`} className="trow">
                  <div className="cell key">{item.seed?.gemstoneName || item.uniqueKey}</div>
                  <div className="cell" data-label="Search term">{item.seed?.searchTerm || item.searchKeywords || '—'}</div>
                  <div className="cell" data-label="Stage"><span className={`badge ${tone(item.stage)}`}>{ACTION_LABEL[item.stage as keyof typeof ACTION_LABEL]}</span></div>
                  <div className="cell r">{ago(item.updatedAt)}</div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty">
              <b>Nothing waiting on you</b>
              <span>When a draft needs your decision or a rewrite lands in your name, it shows up here.</span>
            </div>
          )}

          {canApprove(user) && pending.length > 0 && (
            <>
              <div className="eyebrow" style={{ margin: '26px 0 10px' }}>Queued by AI · not yet pulled in</div>
              <div className="card">
                <h2>{c.stage1} row{c.stage1 === 1 ? '' : 's'} waiting in AI_Content_Queue</h2>
                <p>Pulling them in creates one Stage 2 approval request each.</p>
                {pending.slice(0, 6).map(row => (
                  <div key={row.uniqueKey} className="intake-row">
                    <div className="t">
                      <b>{row.gemstoneName || row.uniqueKey}</b>
                      <span>{row.searchTerm} · {row.intent} · {row.contentType}</span>
                    </div>
                    <div className="sv">{row.searchVolume?.toLocaleString('en-IN') ?? '—'} SV</div>
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="eyebrow" style={{ margin: '26px 0 10px' }}>Recent activity</div>
          {recent.length ? (
            <div className="table" style={{ '--cols': 'minmax(0,1.6fr) minmax(0,1fr) 170px 110px' } as React.CSSProperties}>
              {recent.map(item => (
                <Link key={item.uniqueKey} href={`/content/${item.uniqueKey}`} className="trow">
                  <div className="cell key">{item.seed?.gemstoneName || item.uniqueKey}</div>
                  <div className="cell" data-label="With">{item.assigneeEmail || '—'}</div>
                  <div className="cell" data-label="Stage"><span className={`badge ${tone(item.stage)}`}>{ACTION_LABEL[item.stage as keyof typeof ACTION_LABEL]}</span></div>
                  <div className="cell r">{ago(item.updatedAt)}</div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty">
              <b>No content in the workflow yet</b>
              <span>Once AI drafts are pulled in, every piece shows here.</span>
            </div>
          )}
        </div>
      </main>
    </>
  )
}

import Link from 'next/link'
import { notFound, redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/auth'
import { listItems, pendingSeeds, attachSeeds } from '@/lib/store'
import { STAGES, ACTION_LABEL, TERMINAL } from '@/lib/types'
import type { Item, SeedRow } from '@/lib/types'

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

export default async function StagePage({ params, searchParams }: {
  params: { stage: string }
  searchParams: { q?: string; flash?: string; tone?: string }
}) {
  const stageNum = Number(params.stage)
  if (![1,2,3,4,5].includes(stageNum)) notFound()

  const user = await getCurrentUser()
  if (!user) redirect('/')

  const stageMeta = STAGES[stageNum]
  const q = (searchParams.q ?? '').toLowerCase().trim()

  // Stage 1 = AI queue (pending seeds not yet in workflow)
  let rows: (Item | SeedRow)[] = []
  if (stageNum === 1) {
    rows = await pendingSeeds()
  } else {
    const allItems = await listItems()
    const filtered = allItems.filter(i => stageMeta.actions.includes(i.stage as never))
    const withSeeds = await attachSeeds(filtered)
    rows = withSeeds
  }

  const displayRows = q ? rows.filter(r => {
    if (stageNum === 1) {
      const s = r as SeedRow
      return [s.uniqueKey, s.gemstoneName, s.searchTerm, s.category, s.intent].join(' ').toLowerCase().includes(q)
    }
    const i = r as Item & { seed: SeedRow | null }
    return [i.uniqueKey, i.seed?.gemstoneName, i.seed?.searchTerm, i.category, i.assigneeEmail].join(' ').toLowerCase().includes(q)
  }) : rows

  return (
    <>
      <div className="page-top">
        <div>
          <h1>Stage {stageNum} · {stageMeta.label}</h1>
          <div className="page-top-sub">{displayRows.length} item{displayRows.length === 1 ? '' : 's'}{q ? ` matching "${q}"` : ''}</div>
        </div>
      </div>
      <main>
        <div className="wrap">
          {searchParams.flash && (
            <div className={`flash ${searchParams.tone ?? 'good'}`} style={{ marginBottom: 14 }}>{searchParams.flash}</div>
          )}

          <form className="search" action="">
            <input name="q" defaultValue={q} placeholder={`Search ${stageMeta.label.toLowerCase()}…`} />
            <button type="submit">Search</button>
          </form>

          {stageNum === 1 ? (
            /* Stage 1 — seed rows from AI_Content_Queue */
            displayRows.length ? (
              <div className="table" style={{ '--cols': 'minmax(0,1.4fr) minmax(0,1.2fr) 80px 110px 140px 100px' } as React.CSSProperties}>
                <div className="thead">
                  <div>Gemstone / Topic</div>
                  <div>Search term</div>
                  <div>SV</div>
                  <div>Intent</div>
                  <div>Type</div>
                  <div>Priority</div>
                </div>
                {displayRows.map(r => {
                  const s = r as SeedRow
                  return (
                    <div key={s.uniqueKey} className="trow">
                      <div className="cell key">{s.gemstoneName || s.uniqueKey}</div>
                      <div className="cell" data-label="Search term">{s.searchTerm || '—'}</div>
                      <div className="cell" data-label="SV">{s.searchVolume?.toLocaleString('en-IN') ?? '—'}</div>
                      <div className="cell" data-label="Intent">{s.intent || '—'}</div>
                      <div className="cell" data-label="Type">{s.contentType || '—'}</div>
                      <div className="cell" data-label="Priority">{s.priority ? <span className={`badge${s.priority === 'High' ? ' warn' : ''}`}>{s.priority}</span> : '—'}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty">
                <b>Nothing queued</b>
                <span>All ready rows in AI_Content_Queue are already in the workflow, or none have been generated yet.</span>
              </div>
            )
          ) : (
            /* Stages 2–5 — workflow items */
            displayRows.length ? (
              <div className="table" style={{ '--cols': 'minmax(0,1.5fr) minmax(0,1.2fr) 80px 110px 160px minmax(0,1fr) 100px' } as React.CSSProperties}>
                <div className="thead">
                  <div>Gemstone / Topic</div>
                  <div>Search term</div>
                  <div>SV</div>
                  <div>Intent</div>
                  <div>Stage</div>
                  <div>With</div>
                  <div className="r">Updated</div>
                </div>
                {displayRows.map(r => {
                  const item = r as Item & { seed: SeedRow | null }
                  return (
                    <Link key={item.uniqueKey} href={`/content/${item.uniqueKey}`} className="trow">
                      <div className="cell key">
                        {item.seed?.gemstoneName || item.uniqueKey}
                        {item.seed?.priority === 'High' && <span className="badge warn" style={{ marginLeft: 6 }}>High</span>}
                      </div>
                      <div className="cell" data-label="Search term">{item.seed?.searchTerm || item.searchKeywords || '—'}</div>
                      <div className="cell" data-label="SV">{(item.seed?.searchVolume ?? item.searchVolume)?.toLocaleString('en-IN') ?? '—'}</div>
                      <div className="cell" data-label="Intent">{item.seed?.intent || '—'}</div>
                      <div className="cell" data-label="Stage">
                        <span className={`badge ${tone(item.stage)}`}>{ACTION_LABEL[item.stage as keyof typeof ACTION_LABEL]}</span>
                        {(item.revisionNumber ?? 0) > 0 && <span className="src"> · r{item.revisionNumber}</span>}
                      </div>
                      <div className={`cell${item.assigneeUserId === user.id ? ' mine' : ''}`} data-label="With">
                        {item.assigneeEmail || '—'}
                      </div>
                      <div className="cell r" data-label="Updated">{ago(item.updatedAt)}</div>
                    </Link>
                  )
                })}
              </div>
            ) : (
              <div className="empty">
                <b>{q ? 'No match' : `Nothing in Stage ${stageNum}`}</b>
                <span>{q ? `Nothing matches "${q}".` : 'No items are currently at this stage.'}</span>
                {q && <Link href={`/stage/${stageNum}`} className="btn" style={{ marginTop: 14, display: 'inline-flex' }}>Clear search</Link>}
              </div>
            )
          )}
        </div>
      </main>
    </>
  )
}

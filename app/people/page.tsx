import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/auth'
import { listUsers, saveUser, setUserActive } from '@/lib/store'
import { isAdmin } from '@/lib/types'

export default async function PeoplePage({ searchParams }: { searchParams: { flash?: string; tone?: string } }) {
  const user = await getCurrentUser()
  if (!user || !isAdmin(user)) redirect('/dashboard')
  const people = await listUsers()

  async function doSave(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !isAdmin(actor)) return
    const email = String(fd.get('email') ?? '').trim().toLowerCase()
    const role  = String(fd.get('role') ?? 'viewer') as 'admin' | 'approver' | 'writer' | 'viewer'
    const username = String(fd.get('username') ?? '').trim() || undefined
    const { listUsers: lu, saveUser: su } = await import('@/lib/store')
    try {
      const existing = (await lu()).find(u => u.email === email)
      await su({ email, username, role, isActive: true, userId: existing?.id, createdAt: existing?.createdAt ?? undefined })
      redirect('/people?flash=Saved&tone=good')
    } catch (e: unknown) { redirect(`/people?flash=${encodeURIComponent(String((e as Error).message))}&tone=danger`) }
  }

  async function doToggle(fd: FormData) {
    'use server'
    const actor = await getCurrentUser()
    if (!actor || !isAdmin(actor)) return
    const id = Number(fd.get('user_id'))
    const active = fd.get('active') === '1'
    if (id === actor.id) { redirect('/people?flash=You+cannot+revoke+your+own+access&tone=danger') }
    await setUserActive(id, active)
    redirect('/people?flash=Access+updated&tone=good')
  }

  const ROLES = ['admin','approver','writer','viewer']
  const ROLE_LABEL: Record<string, string> = { admin: 'Admin', approver: 'Approver', writer: 'Writer', viewer: 'Viewer' }

  return (
    <>
      <div className="page-top"><h1>People</h1></div>
      <main>
        <div className="wrap narrow">
          {searchParams.flash && <div className={`flash ${searchParams.tone ?? 'good'}`} style={{ marginBottom: 14 }}>{decodeURIComponent(searchParams.flash)}</div>}

          <div className="table" style={{ '--cols': 'minmax(0,1.4fr) minmax(0,1.4fr) 120px 100px' } as React.CSSProperties}>
            <div className="thead">
              <div>Name</div><div>Email</div><div>Role</div><div className="r">Access</div>
            </div>
            {people.map(p => (
              <div key={p.id} className="trow">
                <div className="cell key">{p.username}{p.id === user.id && <span className="src"> · you</span>}</div>
                <div className="cell" data-label="Email">{p.email}</div>
                <div className="cell" data-label="Role">
                  <span className={`badge${['admin','approver'].includes(p.role) ? ' accent' : ''}`}>{ROLE_LABEL[p.role]}</span>
                </div>
                <div className="cell r" data-label="Access">
                  {p.id === user.id ? <span className="src">—</span> : (
                    <form action={doToggle} style={{ display: 'inline' }}>
                      <input type="hidden" name="user_id" value={p.id} />
                      <input type="hidden" name="active" value={p.isActive ? '0' : '1'} />
                      <button className="btn quiet" type="submit" style={{ fontSize: 12, padding: '5px 10px' }}>
                        {p.isActive ? 'Revoke' : 'Restore'}
                      </button>
                    </form>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="card" style={{ marginTop: 18 }}>
            <h2>Add someone or change a role</h2>
            <p>Use an existing email to change that person's role — the newest entry wins.</p>
            <form action={doSave} className="stack">
              <div>
                <label className="lab" htmlFor="email">Work email</label>
                <input className="field" type="email" name="email" id="email" required placeholder="name@gempundit.com" />
              </div>
              <div>
                <label className="lab" htmlFor="username">Name <span className="hint">· optional</span></label>
                <input className="field" name="username" id="username" placeholder="Taken from email if blank" />
              </div>
              <div>
                <label className="lab" htmlFor="role">Role</label>
                <select className="field" name="role" id="role">
                  <option value="writer">Writer — receives content to rewrite (Kirti)</option>
                  <option value="approver">Approver — decides on drafts and submissions (Vivek)</option>
                  <option value="viewer">Viewer — read-only</option>
                  <option value="admin">Admin — everything plus this screen</option>
                </select>
              </div>
              <button className="btn primary" type="submit">Save</button>
            </form>
          </div>
        </div>
      </main>
    </>
  )
}

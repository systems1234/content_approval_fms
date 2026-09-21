'use client'

import { useState, useEffect, useTransition } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { signOut } from 'next-auth/react'
import type { User } from '@/lib/types'

const ChevronLeft  = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
const ChevronRight = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
const MenuIcon     = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
const GridIcon     = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
const BotIcon      = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
const CheckIcon    = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
const PenIcon      = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
const EyeIcon      = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
const AwardIcon    = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>
const UsersIcon    = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
const LogOutIcon   = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>

function inits(u: User) {
  const parts = u.username.replace(/\./g, ' ').split(' ').filter(Boolean)
  return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase() || u.email.slice(0, 2).toUpperCase()
}

interface Props {
  user: User
  users: User[]       // empty when SSO is on
  stageCounts: { stage1: number; stage2: number; stage3: number; stage4: number; stage5: number; needsYou: number; closed: number; open: number }
  canApprove: boolean
  isAdmin: boolean
  requireSignin: boolean
}

export default function Sidebar({ user, users, stageCounts, canApprove, isAdmin, requireSignin }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  useEffect(() => {
    if (localStorage.getItem('sidebar-collapsed') === '1') setCollapsed(true)
  }, [])

  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem('sidebar-collapsed', next ? '1' : '0')
  }

  const switchActor = (email: string) => {
    startTransition(async () => {
      await fetch('/api/auth/switch', { method: 'POST', body: JSON.stringify({ email }), headers: { 'Content-Type': 'application/json' } })
      router.refresh()
    })
  }

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/')

  const stages = [
    { n: 1, label: 'AI Content',     count: stageCounts.stage1, icon: <BotIcon />,   href: '/stage/1' },
    { n: 2, label: 'Vivek Approval', count: stageCounts.stage2, icon: <CheckIcon />,  href: '/stage/2' },
    { n: 3, label: 'Kirti Writing',  count: stageCounts.stage3, icon: <PenIcon />,    href: '/stage/3' },
    { n: 4, label: 'Vivek Review',   count: stageCounts.stage4, icon: <EyeIcon />,    href: '/stage/4' },
    { n: 5, label: 'Completed',      count: stageCounts.stage5, icon: <AwardIcon />,  href: '/stage/5' },
  ]

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      {/* Brand + collapse toggle in the same row */}
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--hair)', padding: '12px 10px' }}>
        <Link href="/dashboard" className="sidebar-brand" style={{ borderBottom: 'none', padding: '4px', flex: 1 }}>
          <div className="sidebar-brand-icon">C</div>
          <div><b>content</b><span style={{ marginLeft: 4 }}>fms</span></div>
        </Link>
        <button
          onClick={toggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            border: 0, background: collapsed ? 'var(--accent-soft)' : 'none',
            cursor: 'pointer', color: collapsed ? 'var(--accent-deep)' : 'var(--muted)',
            borderRadius: 6, width: 28, height: 28,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {collapsed ? <ChevronRight /> : <ChevronLeft />}
        </button>
      </div>

      <div className="sidebar-scroll">
        <Link href="/dashboard" className={`nav-item${isActive('/dashboard') ? ' active' : ''}`}>
          <span className="ni"><GridIcon /></span>
          <span className="nl">Dashboard</span>
          {stageCounts.needsYou > 0 && <span className="nc live">{stageCounts.needsYou}</span>}
        </Link>

        <div className="sidebar-section">Stages</div>
        {stages.map(s => (
          <Link key={s.n} href={s.href} className={`nav-item${isActive(s.href) ? ' active' : ''}`}>
            <span className="ni">{s.icon}</span>
            <span className="nl">Stage {s.n} · {s.label}</span>
            {s.count > 0 && <span className={`nc${[2, 4].includes(s.n) ? ' live' : ''}`}>{s.count}</span>}
          </Link>
        ))}

        {isAdmin && (
          <>
            <div className="sidebar-section">Admin</div>
            <Link href="/people" className={`nav-item${isActive('/people') ? ' active' : ''}`}>
              <span className="ni"><UsersIcon /></span>
              <span className="nl">People</span>
            </Link>
          </>
        )}

        {/* Dev-only actor switcher — hidden when SSO is on */}
        {!requireSignin && users.length > 1 && (
          <>
            <div className="sidebar-section">Acting as</div>
            {users.map(u => (
              <button
                key={u.id}
                className={`nav-item${u.id === user.id ? ' active' : ''}`}
                style={{ width: '100%', textAlign: 'left', border: 0 }}
                onClick={() => switchActor(u.email)}
                disabled={isPending || u.id === user.id}
              >
                <span className="ni">
                  <div style={{ width: 18, height: 18, borderRadius: '50%', background: u.id === user.id ? 'var(--accent)' : 'var(--ghost)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 700 }}>
                    {inits(u)[0]}
                  </div>
                </span>
                <span className="nl">{u.username}</span>
              </button>
            ))}
          </>
        )}
      </div>

      {/* Bottom: user info + sign out */}
      <div className="sidebar-bottom">
        <div className="sidebar-user">
          <div className="avatar">{inits(user)}</div>
          <div className="sidebar-user-info">
            <b>{user.username}</b>
            <span>{user.role.charAt(0).toUpperCase() + user.role.slice(1)}</span>
          </div>
        </div>
        {requireSignin && (
          <button
            className="nav-item"
            style={{ width: '100%', textAlign: 'left', border: 0, color: 'var(--muted)' }}
            onClick={() => signOut({ callbackUrl: '/signin' })}
          >
            <span className="ni"><LogOutIcon /></span>
            <span className="nl">Sign out</span>
          </button>
        )}
      </div>
    </aside>
  )
}

import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import { getCurrentUser } from '@/lib/auth'
import { listUsers, counts as getCounts } from '@/lib/store'
import { canApprove, isAdmin } from '@/lib/types'

export const metadata: Metadata = { title: 'Content FMS · GemPundit' }

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  let user = null, users: Awaited<ReturnType<typeof listUsers>> = [], stageCounts = null

  try {
    user = await getCurrentUser()
    if (user) {
      const [all, c] = await Promise.all([listUsers(true), getCounts(user)])
      users = all
      stageCounts = c
    }
  } catch { /* BQ not configured yet */ }

  if (!user) {
    return (
      <html lang="en"><body>
        <div className="center-page">
          <div className="center-box">
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <b style={{ fontSize: 22, fontWeight: 700 }}>content</b>
              <span style={{ fontSize: 13, color: 'var(--muted)' }}>approval</span>
            </div>
            <div className="center-panel">
              <h1>Nobody to act as</h1>
              <p>
                No active user found in <span className="mono">Content_FMS.Users</span>.<br />
                Run <span className="mono">seed_sample_data.sql</span> in BigQuery first,
                then add <span className="mono">GOOGLE_APPLICATION_CREDENTIALS_JSON</span> to Vercel env vars.
              </p>
            </div>
          </div>
        </div>
        <footer>GemPundit · Content FMS · all times IST</footer>
      </body></html>
    )
  }

  return (
    <html lang="en">
      <body>
        <Sidebar
          user={user}
          users={users}
          stageCounts={stageCounts ?? { stage1: 0, stage2: 0, stage3: 0, stage4: 0, stage5: 0, needsYou: 0, closed: 0, open: 0 }}
          canApprove={canApprove(user)}
          isAdmin={isAdmin(user)}
        />
        <div className="main-area">
          {children}
          <footer>GemPundit · Content FMS · all times IST</footer>
        </div>
      </body>
    </html>
  )
}

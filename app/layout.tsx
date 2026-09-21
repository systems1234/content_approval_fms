import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import { getCurrentUser } from '@/lib/auth'
import { listUsers, counts as getCounts } from '@/lib/store'
import { canApprove, isAdmin } from '@/lib/types'

export const metadata: Metadata = { title: 'Content FMS · GemPundit' }

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const requireSignin = process.env.REQUIRE_SIGNIN === '1'
  let user = null, users: Awaited<ReturnType<typeof listUsers>> = [], stageCounts = null

  try {
    user = await getCurrentUser()
    if (user) {
      const [all, c] = await Promise.all([
        requireSignin ? Promise.resolve([]) : listUsers(true),
        getCounts(user),
      ])
      users = all
      stageCounts = c
    }
  } catch { /* BQ not configured yet */ }

  // Not signed in
  if (!user) {
    return (
      <html lang="en"><body>
        {children}
        <footer>GemPundit · Content FMS · all times IST</footer>
      </body></html>
    )
  }

  return (
    <html lang="en">
      <body>
        <Sidebar
          user={user}
          users={requireSignin ? [] : users}
          stageCounts={stageCounts ?? { stage1: 0, stage2: 0, stage3: 0, stage4: 0, stage5: 0, needsYou: 0, closed: 0, open: 0 }}
          canApprove={canApprove(user)}
          isAdmin={isAdmin(user)}
          requireSignin={requireSignin}
        />
        <div className="main-area">
          {children}
          <footer>GemPundit · Content FMS · all times IST</footer>
        </div>
      </body>
    </html>
  )
}

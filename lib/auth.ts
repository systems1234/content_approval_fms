import { cookies, headers } from 'next/headers'
import { getUserByEmail, listUsers } from './store'
import type { User } from './types'

const requireSignin = () => process.env.REQUIRE_SIGNIN === '1'

export async function getCurrentUser(): Promise<User | null> {
  try {
    if (requireSignin()) {
      // Use NextAuth session — read session token from cookie and decode
      const { getServerSession } = await import('next-auth')
      const session = await getServerSession()
      if (!session?.user?.email) return null
      return getUserByEmail(session.user.email)
    }

    // Dev mode: cookie-based actor switching
    const store = await cookies()
    const email = store.get('acting_as')?.value?.toLowerCase()
      ?? (process.env.DEFAULT_ACTOR_EMAIL ?? 'vivek@gempundit.com').toLowerCase()
    let user = await getUserByEmail(email)
    if (!user) {
      const all = await listUsers(true)
      user = all[0] ?? null
    }
    return user
  } catch {
    return null
  }
}

export async function requireUser(): Promise<User> {
  const u = await getCurrentUser()
  if (!u) throw new Error('No active user found.')
  return u
}

export function isSigninRequired(): boolean {
  return requireSignin()
}

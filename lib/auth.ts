import { cookies } from 'next/headers'
import { getUserByEmail, listUsers } from './store'
import type { User } from './types'

export async function getCurrentUser(): Promise<User | null> {
  try {
    const store = await cookies()
    const email = store.get('acting_as')?.value?.toLowerCase()
      ?? (process.env.DEFAULT_ACTOR_EMAIL ?? 'vivek@gempundit.com').toLowerCase()
    let user = await getUserByEmail(email)
    if (!user) {
      // first boot: return the first active user in the table
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
  if (!u) throw new Error('No active user found. Run seed_sample_data.sql or bootstrap_admin.py.')
  return u
}

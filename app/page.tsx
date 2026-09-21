import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/auth'

export default async function Home() {
  const user = await getCurrentUser()
  if (!user) {
    if (process.env.REQUIRE_SIGNIN === '1') redirect('/signin')
    // dev mode with no users at all
    redirect('/dashboard')
  }
  redirect('/dashboard')
}

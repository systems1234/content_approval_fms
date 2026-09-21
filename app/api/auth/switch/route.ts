import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function POST(req: Request) {
  const { email } = await req.json()
  const store = await cookies()
  store.set('acting_as', String(email).toLowerCase(), { httpOnly: true, sameSite: 'lax', path: '/' })
  return NextResponse.json({ ok: true })
}

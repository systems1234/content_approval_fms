import { NextResponse } from 'next/server'
import { syncAIDrafts } from '@/lib/store'

export async function POST(req: Request) {
  const expected = process.env.WORKFLOW_API_KEY
  if (expected && req.headers.get('X-API-Key') !== expected)
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  try {
    const result = await syncAIDrafts()
    return NextResponse.json({ ok: true, ...result })
  } catch (e: unknown) {
    return NextResponse.json({ error: String((e as Error).message) }, { status: 400 })
  }
}

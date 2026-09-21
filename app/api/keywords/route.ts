import { NextResponse } from 'next/server'
import { run, ref, nowIST } from '@/lib/bq'

export async function POST(req: Request) {
  const expected = process.env.WORKFLOW_API_KEY
  if (expected && req.headers.get('X-API-Key') !== expected)
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const body = await req.json()
  const key  = String(body.unique_key ?? '').trim()
  if (!key) return NextResponse.json({ error: 'unique_key required' }, { status: 400 })
  // Just forward to the workflow table as a KEYWORDS_READY event
  const eventId = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
  await run(
    `INSERT INTO ${ref('Content_Approval_Workflow')} (event_id,timestamp,unique_key,action,search_keywords,search_volume,source_row_id)
     VALUES (?,?,?,?,?,?,?)`,
    [eventId, nowIST(), key, 'KEYWORDS_READY', body.search_keywords ?? null, body.search_volume ?? null, body.source_row_id ?? null],
    ['STRING','DATETIME','STRING','STRING','STRING','INT64','STRING']
  )
  return NextResponse.json({ ok: true, unique_key: key, stage: 'KEYWORDS_READY' }, { status: 201 })
}

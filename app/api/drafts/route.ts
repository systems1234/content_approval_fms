import { NextResponse } from 'next/server'
import { run, ref, nowIST } from '@/lib/bq'

export async function POST(req: Request) {
  const expected = process.env.WORKFLOW_API_KEY
  if (expected && req.headers.get('X-API-Key') !== expected)
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const body = await req.json()
  const key  = String(body.unique_key ?? '').trim()
  if (!key) return NextResponse.json({ error: 'unique_key required' }, { status: 400 })
  if (!body.content_text && !body.content_url)
    return NextResponse.json({ error: 'content_text or content_url required' }, { status: 400 })
  const eventId = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
  await run(
    `INSERT INTO ${ref('Content_Approval_Workflow')} (event_id,timestamp,unique_key,category,action,content_text,content_url,word_count,search_keywords,search_volume,source_row_id,source_payload)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
    [eventId, nowIST(), key, body.category ?? null, 'DRAFT_RECEIVED', body.content_text ?? null, body.content_url ?? null,
     body.word_count ?? null, body.search_keywords ?? null, body.search_volume ?? null,
     body.source_row_id ?? null, JSON.stringify(body)],
    ['STRING','DATETIME','STRING','STRING','STRING','STRING','STRING','INT64','STRING','INT64','STRING','STRING']
  )
  return NextResponse.json({ ok: true, unique_key: key, stage: 'DRAFT_RECEIVED' }, { status: 201 })
}

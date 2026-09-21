import {
  ref, run, nowIST, toStr, toInt, toFloat, toBool, toDateStr,
} from './bq'
import {
  Action, Item, SeedRow, User, WorkflowEvent,
  ALLOWED_NEXT, TERMINAL,
} from './types'

// ----- helpers -------------------------------------------------------------

function genId(): string {
  // crypto.randomUUID is available in Node 19+; fallback uses Math.random
  try {
    return (crypto as typeof crypto).randomUUID().replace(/-/g, '')
  } catch {
    return Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
  }
}

export class WorkflowError extends Error {}

function guard(currentStage: string | undefined, next: Action) {
  const allowed = ALLOWED_NEXT[currentStage ?? ''] ?? []
  if (!allowed.includes(next)) {
    if (currentStage && TERMINAL.includes(currentStage as Action))
      throw new WorkflowError('This request is closed.')
    throw new WorkflowError(`Can't go from "${currentStage ?? 'nothing'}" to "${next}".`)
  }
}

const CARRY: (keyof WorkflowEvent)[] = [
  'category', 'assigneeUserId', 'assigneeEmail', 'contentText',
  'contentUrl', 'wordCount', 'searchKeywords', 'searchVolume',
  'sourceRowId', 'sourcePayload',
]

function rowToEvent(r: Record<string, unknown>): WorkflowEvent {
  return {
    eventId:         toStr(r.event_id)        ?? '',
    timestamp:       toDateStr(r.timestamp)   ?? '',
    uniqueKey:       toStr(r.unique_key)      ?? '',
    category:        toStr(r.category),
    action:          toStr(r.action)          as Action,
    actorUserId:     toInt(r.actor_user_id),
    actorEmail:      toStr(r.actor_email),
    assigneeUserId:  toInt(r.assignee_user_id),
    assigneeEmail:   toStr(r.assignee_email),
    contentText:     toStr(r.content_text),
    contentUrl:      toStr(r.content_url),
    wordCount:       toInt(r.word_count),
    searchKeywords:  toStr(r.search_keywords),
    searchVolume:    toInt(r.search_volume),
    comment:         toStr(r.comment),
    revisionNumber:  toInt(r.revision_number),
    sourceRowId:     toStr(r.source_row_id),
    sourcePayload:   toStr(r.source_payload),
  }
}

function rowToUser(r: Record<string, unknown>): User {
  return {
    id:        toInt(r.user_id)    ?? 0,
    username:  toStr(r.username)   ?? '',
    email:     (toStr(r.email)     ?? '').toLowerCase(),
    role:      (toStr(r.role)      ?? 'viewer') as User['role'],
    isActive:  toBool(r.is_active),
    createdAt: toDateStr(r.created_at) ?? null,
  }
}

function rowToSeed(r: Record<string, unknown>): SeedRow {
  return {
    uniqueKey:        toStr(r.unique_key)         ?? '',
    generatedAt:      toDateStr(r.generated_at)   ?? '',
    status:           toStr(r.status),
    category:         toStr(r.category),
    gemstoneName:     toStr(r.gemstone_name),
    searchTerm:       toStr(r.search_term),
    secondaryKeywords:toStr(r.secondary_keywords),
    searchVolume:     toInt(r.search_volume),
    keywordDifficulty:toInt(r.keyword_difficulty),
    intent:           toStr(r.intent),
    contentType:      toStr(r.content_type),
    language:         toStr(r.language),
    priority:         toStr(r.priority),
    plannedDate:      toDateStr(r.planned_date),
    targetUrl:        toStr(r.target_url),
    metaTitle:        toStr(r.meta_title),
    metaDescription:  toStr(r.meta_description),
    aiDraft:          toStr(r.ai_draft),
    aiDraftUrl:       toStr(r.ai_draft_url),
    wordCount:        toInt(r.word_count),
    aiModel:          toStr(r.ai_model),
    aiConfidence:     toFloat(r.ai_confidence),
    researchNotes:    toStr(r.research_notes),
  }
}

function foldEvents(events: WorkflowEvent[]): Item {
  const sorted = [...events].sort((a, b) =>
    a.timestamp.localeCompare(b.timestamp) || a.eventId.localeCompare(b.eventId))
  const first = sorted[0]
  const last  = sorted[sorted.length - 1]

  const carried: Partial<WorkflowEvent> = {}
  for (const ev of sorted) {
    for (const field of CARRY) {
      const v = ev[field]
      if (v !== null && v !== undefined && v !== '') carried[field] = v as never
    }
  }

  return {
    uniqueKey:       last.uniqueKey,
    stage:           last.action,
    category:        carried.category       as string | undefined,
    assigneeUserId:  carried.assigneeUserId as number | undefined,
    assigneeEmail:   carried.assigneeEmail  as string | undefined,
    contentText:     carried.contentText    as string | undefined,
    contentUrl:      carried.contentUrl     as string | undefined,
    wordCount:       carried.wordCount      as number | undefined,
    searchKeywords:  carried.searchKeywords as string | undefined,
    searchVolume:    carried.searchVolume   as number | undefined,
    revisionNumber:  Math.max(...sorted.map(e => e.revisionNumber ?? 0)),
    lastComment:     last.comment,
    lastActorEmail:  last.actorEmail,
    createdAt:       first.timestamp,
    updatedAt:       last.timestamp,
    history:         sorted,
    seed:            null,
  }
}

// Insert one or multiple rows into a workflow table
async function insertEvents(rows: Record<string, unknown>[]) {
  if (!rows.length) return
  const cols = [
    'event_id','timestamp','unique_key','category','action',
    'actor_user_id','actor_email','assignee_user_id','assignee_email',
    'content_text','content_url','word_count','search_keywords','search_volume',
    'comment','revision_number','source_row_id','source_payload',
  ]
  const colTypes: Record<string, string> = {
    actor_user_id: 'INT64', assignee_user_id: 'INT64',
    word_count: 'INT64', search_volume: 'INT64', revision_number: 'INT64',
    timestamp: 'DATETIME',
  }
  const used = cols.filter(c => rows.some(r => r[c] !== undefined && r[c] !== null))
  const params: unknown[] = []
  const types: string[]   = []
  const tuples = rows.map(row => {
    const vals = used.map(c => {
      params.push(row[c] ?? null)
      types.push(colTypes[c] ?? 'STRING')
      return '?'
    })
    return `(${vals.join(', ')})`
  })
  const sql = `INSERT INTO ${ref('Content_Approval_Workflow')} (${used.join(', ')}) VALUES ${tuples.join(', ')}`
  await run(sql, params as never[], types)
}

function makeEvent(
  uniqueKey: string,
  action: Action,
  extra: Partial<Omit<WorkflowEvent, 'eventId' | 'timestamp' | 'uniqueKey' | 'action'>> = {}
): Record<string, unknown> {
  return {
    event_id:        genId(),
    timestamp:       nowIST(),
    unique_key:      uniqueKey,
    action,
    category:        extra.category,
    actor_user_id:   extra.actorUserId,
    actor_email:     extra.actorEmail,
    assignee_user_id:extra.assigneeUserId,
    assignee_email:  extra.assigneeEmail,
    content_text:    extra.contentText,
    content_url:     extra.contentUrl,
    word_count:      extra.wordCount,
    search_keywords: extra.searchKeywords,
    search_volume:   extra.searchVolume,
    comment:         extra.comment,
    revision_number: extra.revisionNumber,
    source_row_id:   extra.sourceRowId,
    source_payload:  extra.sourcePayload,
  }
}

// ----- users ---------------------------------------------------------------

async function latestUsers(where = '', params: unknown[] = [], types: string[] = []) {
  const sql = `
    SELECT * EXCEPT(rn) FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY updated_at DESC) AS rn
      FROM ${ref('Users')} ${where}
    ) WHERE rn = 1 ORDER BY username`
  return (await run(sql, params as never[], types)).map(rowToUser)
}

export async function getUser(userId: number): Promise<User | null> {
  const rows = await latestUsers('WHERE user_id = ?', [userId], ['INT64'])
  return rows.find(u => u.isActive) ?? null
}

export async function getUserByEmail(email: string): Promise<User | null> {
  const rows = await latestUsers('WHERE LOWER(email) = ?', [email.toLowerCase()], ['STRING'])
  return rows.find(u => u.isActive) ?? null
}

export async function listUsers(activeOnly = false): Promise<User[]> {
  const users = await latestUsers()
  return activeOnly ? users.filter(u => u.isActive) : users
}

export async function writers(): Promise<User[]> {
  return (await listUsers(true)).filter(u => ['admin', 'approver', 'writer'].includes(u.role))
}

export async function saveUser(opts: {
  email: string; username?: string; role: User['role']
  isActive?: boolean; userId?: number; createdAt?: string
}) {
  const now = nowIST()
  const userId = opts.userId ?? toInt(Date.now())!
  const sql = `INSERT INTO ${ref('Users')} (user_id,username,email,password_hash,role,is_active,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?)`
  await run(sql,
    [userId, opts.username ?? opts.email.split('@')[0], opts.email.toLowerCase(), '', opts.role, opts.isActive ?? true, opts.createdAt ?? now, now],
    ['INT64','STRING','STRING','STRING','STRING','BOOL','DATETIME','DATETIME'])
}

export async function setUserActive(userId: number, active: boolean) {
  const rows = await latestUsers('WHERE user_id = ?', [userId], ['INT64'])
  if (!rows[0]) throw new WorkflowError('No such user.')
  const u = rows[0]
  await saveUser({ email: u.email, username: u.username, role: u.role, isActive: active, userId: u.id, createdAt: u.createdAt ?? undefined })
}

// ----- reading items -------------------------------------------------------

async function allEvents(uniqueKey?: string): Promise<WorkflowEvent[]> {
  const where = uniqueKey ? 'WHERE unique_key = ?' : ''
  const params = uniqueKey ? [uniqueKey] : []
  const sql = `SELECT * FROM ${ref('Content_Approval_Workflow')} ${where} ORDER BY timestamp ASC, event_id ASC`
  return (await run(sql, params as never[], ['STRING'])).map(rowToEvent)
}

export async function listItems(): Promise<Item[]> {
  const events = await allEvents()
  const grouped: Record<string, WorkflowEvent[]> = {}
  for (const ev of events) grouped[ev.uniqueKey] = [...(grouped[ev.uniqueKey] ?? []), ev]
  const items = Object.values(grouped).map(foldEvents)
  items.sort((a, b) => (b.updatedAt ?? '').localeCompare(a.updatedAt ?? ''))
  return items
}

export async function getItem(uniqueKey: string): Promise<Item | null> {
  const events = await allEvents(uniqueKey)
  return events.length ? foldEvents(events) : null
}

export async function attachSeeds(items: Item[]): Promise<Item[]> {
  const table = process.env.AI_SOURCE_TABLE ?? `${process.env.BIGQUERY_PROJECT ?? 'mis-gempundit'}.${process.env.BIGQUERY_DATASET ?? 'Content_FMS'}.AI_Content_Queue`
  if (!items.length) return items
  try {
    const keys = items.map(i => i.uniqueKey)
    const sql = `SELECT * FROM \`${table}\` WHERE unique_key IN UNNEST(@keys)`
    const [rows] = await (await import('./bq')).getClient().query({
      query: sql, params: { keys }, types: { keys: { type: 'ARRAY', arrayType: 'STRING' } },
    })
    const lookup = Object.fromEntries((rows as Record<string, unknown>[]).map(r => [toStr(r.unique_key), rowToSeed(r)]))
    return items.map(i => ({ ...i, seed: lookup[i.uniqueKey] ?? null }))
  } catch {
    return items
  }
}

export async function pendingSeeds(): Promise<SeedRow[]> {
  const table = process.env.AI_SOURCE_TABLE ?? `${process.env.BIGQUERY_PROJECT ?? 'mis-gempundit'}.${process.env.BIGQUERY_DATASET ?? 'Content_FMS'}.AI_Content_Queue`
  try {
    const sql = `
      SELECT * FROM \`${table}\`
      WHERE COALESCE(status, 'READY') = 'READY'
        AND CAST(unique_key AS STRING) NOT IN (
          SELECT DISTINCT unique_key FROM ${ref('Content_Approval_Workflow')}
        )
      ORDER BY generated_at DESC`
    return (await run(sql)).map(rowToSeed)
  } catch { return [] }
}

export async function counts(user: User) {
  const [items, pending] = await Promise.all([listItems(), pendingSeeds()])
  const stage2  = items.filter(i => i.stage === 'DRAFT_RECEIVED').length
  const stage3  = items.filter(i => ['ALLOCATED','REWRITE_REQUESTED'].includes(i.stage)).length
  const stage4  = items.filter(i => i.stage === 'SUBMITTED').length
  const stage5  = items.filter(i => i.stage === 'COMPLETED').length
  const closed  = items.filter(i => ['REJECTED','DELETED'].includes(i.stage)).length

  const needsYou = items.filter(i => {
    if (TERMINAL.includes(i.stage as Action)) return false
    if (['admin','approver'].includes(user.role) && ['DRAFT_RECEIVED','SUBMITTED'].includes(i.stage)) return true
    if (['admin','approver','writer'].includes(user.role) && ['ALLOCATED','REWRITE_REQUESTED'].includes(i.stage) && i.assigneeUserId === user.id) return true
    return false
  }).length

  return { needsYou, stage1: pending.length, stage2, stage3, stage4, stage5, closed, open: stage2 + stage3 + stage4 }
}

// ----- mutations -----------------------------------------------------------

export async function approveAndAllocate(uniqueKey: string, actor: User, assignee: User, comment?: string) {
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'APPROVED')
  await insertEvents([
    makeEvent(uniqueKey, 'APPROVED',   { actorUserId: actor.id, actorEmail: actor.email, category: item?.category, comment }),
    makeEvent(uniqueKey, 'ALLOCATED',  { actorUserId: actor.id, actorEmail: actor.email, category: item?.category, assigneeUserId: assignee.id, assigneeEmail: assignee.email }),
  ])
}

export async function rejectDraft(uniqueKey: string, actor: User, comment?: string) {
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'REJECTED')
  await insertEvents([makeEvent(uniqueKey, 'REJECTED', { actorUserId: actor.id, actorEmail: actor.email, category: item?.category, comment })])
}

export async function submitRewrite(uniqueKey: string, writer: User, contentText?: string, contentUrl?: string, comment?: string) {
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'SUBMITTED')
  if (item?.assigneeUserId !== writer.id && writer.role !== 'admin')
    throw new WorkflowError('This one is allocated to someone else.')
  const text = contentText?.trim()
  const url  = contentUrl?.trim()
  if (!text && !url) throw new WorkflowError('Add the content or a link before submitting.')
  await insertEvents([makeEvent(uniqueKey, 'SUBMITTED', {
    actorUserId: writer.id, actorEmail: writer.email, category: item?.category,
    contentText: text, contentUrl: url, comment,
    revisionNumber: (item?.revisionNumber ?? 0) + 1,
    wordCount: text ? text.split(/\s+/).length : item?.wordCount,
    assigneeUserId: item?.assigneeUserId, assigneeEmail: item?.assigneeEmail,
  })])
}

export async function requestRewrite(uniqueKey: string, actor: User, comment: string) {
  if (!comment?.trim()) throw new WorkflowError('Add a note about what needs changing.')
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'REWRITE_REQUESTED')
  await insertEvents([makeEvent(uniqueKey, 'REWRITE_REQUESTED', {
    actorUserId: actor.id, actorEmail: actor.email, category: item?.category,
    comment: comment.trim(), assigneeUserId: item?.assigneeUserId, assigneeEmail: item?.assigneeEmail,
  })])
}

export async function completeItem(uniqueKey: string, actor: User, comment?: string) {
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'COMPLETED')
  await insertEvents([makeEvent(uniqueKey, 'COMPLETED', { actorUserId: actor.id, actorEmail: actor.email, category: item?.category, comment })])
}

export async function cancelItem(uniqueKey: string, actor: User, comment?: string) {
  const item = await getItem(uniqueKey)
  guard(item?.stage, 'DELETED')
  await insertEvents([makeEvent(uniqueKey, 'DELETED', { actorUserId: actor.id, actorEmail: actor.email, category: item?.category, comment })])
}

export async function syncAIDrafts(): Promise<{ added: number; skipped: string[] }> {
  const pending = await pendingSeeds()
  const events: Record<string, unknown>[] = []
  const skipped: string[] = []
  for (const row of pending) {
    if (!row.aiDraft && !row.aiDraftUrl) { skipped.push(row.uniqueKey); continue }
    events.push(makeEvent(row.uniqueKey, 'DRAFT_RECEIVED', {
      category: row.category, contentText: row.aiDraft, contentUrl: row.aiDraftUrl,
      wordCount: row.wordCount, searchKeywords: row.searchTerm, searchVolume: row.searchVolume,
      sourceRowId: row.uniqueKey, sourcePayload: JSON.stringify(row),
    }))
  }
  // dedupe same key appearing twice
  const seen = new Set<string>(); const deduped = events.filter(e => { const k = e.unique_key as string; if (seen.has(k)) return false; seen.add(k); return true })
  if (deduped.length) await insertEvents(deduped)
  return { added: deduped.length, skipped }
}

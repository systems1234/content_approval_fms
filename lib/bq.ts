import { BigQuery } from '@google-cloud/bigquery'

let _client: BigQuery | null = null

export function getClient(): BigQuery {
  if (_client) return _client
  const credJson = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON?.trim()
  _client = new BigQuery({
    projectId: process.env.BIGQUERY_PROJECT || 'mis-gempundit',
    ...(credJson ? { credentials: JSON.parse(credJson) } : {}),
  })
  return _client
}

const PROJECT  = () => process.env.BIGQUERY_PROJECT || 'mis-gempundit'
const DATASET  = () => process.env.BIGQUERY_DATASET  || 'Content_FMS'
export const ref = (table: string) => `\`${PROJECT()}.${DATASET()}.${table}\``

type Primitive = string | number | boolean | null | undefined

// Run a query. params are positional (@p0, @p1 …) — pass them in order.
export async function run(
  sql: string,
  params: Primitive[] = [],
  types: string[] = [],
): Promise<Record<string, unknown>[]> {
  const namedParams: Record<string, Primitive> = {}
  const namedTypes:  Record<string, string>    = {}
  params.forEach((v, i) => { namedParams[`p${i}`] = v ?? null; namedTypes[`p${i}`] = types[i] || 'STRING' })
  // replace positional markers ?, ?, … with @p0, @p1 …
  let idx = 0
  const query = sql.replace(/\?/g, () => `@p${idx++}`)
  const [rows] = await getClient().query({ query, params: namedParams, types: namedTypes })
  return rows as Record<string, unknown>[]
}

export function nowIST(): string {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
  const p = fmt.formatToParts(new Date())
  const g = (t: string) => p.find(x => x.type === t)?.value ?? '00'
  return `${g('year')}-${g('month')}-${g('day')} ${g('hour')}:${g('minute')}:${g('second')}`
}

// Coerce BQ return values
export function toStr(v: unknown): string | undefined {
  return v == null ? undefined : String(v)
}
export function toInt(v: unknown): number | undefined {
  if (v == null || v === '') return undefined
  const n = typeof v === 'object' && v !== null && 'value' in v
    ? Number((v as { value: unknown }).value)
    : Number(v)
  return isNaN(n) ? undefined : n
}
export function toFloat(v: unknown): number | undefined {
  if (v == null) return undefined
  const n = parseFloat(String(v))
  return isNaN(n) ? undefined : n
}
export function toBool(v: unknown): boolean {
  if (typeof v === 'boolean') return v
  return String(v).toLowerCase() === 'true'
}
export function toDateStr(v: unknown): string | undefined {
  if (v == null) return undefined
  if (typeof v === 'object' && v !== null && 'value' in v)
    return String((v as { value: unknown }).value)
  return String(v)
}

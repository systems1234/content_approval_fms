export type Role = 'admin' | 'approver' | 'writer' | 'viewer'

export type Action =
  | 'KEYWORDS_READY' | 'DRAFT_RECEIVED' | 'APPROVED' | 'ALLOCATED'
  | 'SUBMITTED' | 'REWRITE_REQUESTED' | 'COMPLETED' | 'REJECTED' | 'DELETED'

export const TERMINAL: Action[] = ['COMPLETED', 'REJECTED', 'DELETED']

export const ALLOWED_NEXT: Record<string, Action[]> = {
  '': ['KEYWORDS_READY', 'DRAFT_RECEIVED'],
  KEYWORDS_READY: ['DRAFT_RECEIVED', 'DELETED'],
  DRAFT_RECEIVED: ['APPROVED', 'REJECTED', 'DELETED'],
  APPROVED: ['ALLOCATED', 'DELETED'],
  ALLOCATED: ['SUBMITTED', 'DELETED'],
  SUBMITTED: ['COMPLETED', 'REWRITE_REQUESTED', 'DELETED'],
  REWRITE_REQUESTED: ['SUBMITTED', 'DELETED'],
  COMPLETED: [], REJECTED: [], DELETED: [],
}

// Stage 1 = AI queue (pending seeds, not yet in workflow)
// Stage 2 = Vivek sees AI draft and decides
// Stage 3 = Kirti writes/rewrites
// Stage 4 = Vivek reviews Kirti's version
// Stage 5 = Done
export const STAGES: Record<number, { label: string; tone: string; actions: Action[] }> = {
  1: { label: 'AI Content',      tone: 'neutral', actions: [] },
  2: { label: 'Vivek Approval',  tone: 'warn',    actions: ['DRAFT_RECEIVED'] },
  3: { label: 'Kirti Writing',   tone: 'accent',  actions: ['ALLOCATED', 'REWRITE_REQUESTED'] },
  4: { label: 'Vivek Review',    tone: 'warn',    actions: ['SUBMITTED'] },
  5: { label: 'Completed',       tone: 'good',    actions: ['COMPLETED'] },
}

export function stageForAction(action: Action): number {
  for (const [n, s] of Object.entries(STAGES)) {
    if (s.actions.includes(action)) return Number(n)
  }
  return 0 // REJECTED / DELETED / KEYWORDS_READY
}

export const ACTION_LABEL: Record<Action, string> = {
  KEYWORDS_READY:    'Keywords ready',
  DRAFT_RECEIVED:    'AI draft received',
  APPROVED:          'Approved by Vivek',
  ALLOCATED:         'Allocated to writer',
  SUBMITTED:         'Submitted for review',
  REWRITE_REQUESTED: 'Rewrite requested',
  COMPLETED:         'Completed',
  REJECTED:          'Rejected',
  DELETED:           'Cancelled',
}

export interface User {
  id: number
  username: string
  email: string
  role: Role
  isActive: boolean
  createdAt: string | null
}

export interface WorkflowEvent {
  eventId: string
  timestamp: string
  uniqueKey: string
  category?: string
  action: Action
  actorUserId?: number
  actorEmail?: string
  assigneeUserId?: number
  assigneeEmail?: string
  contentText?: string
  contentUrl?: string
  wordCount?: number
  searchKeywords?: string
  searchVolume?: number
  comment?: string
  revisionNumber?: number
  sourceRowId?: string
  sourcePayload?: string
}

export interface SeedRow {
  uniqueKey: string
  generatedAt: string
  status?: string
  category?: string
  gemstoneName?: string
  searchTerm?: string
  secondaryKeywords?: string
  searchVolume?: number
  keywordDifficulty?: number
  intent?: string
  contentType?: string
  language?: string
  priority?: string
  plannedDate?: string
  targetUrl?: string
  metaTitle?: string
  metaDescription?: string
  aiDraft?: string
  aiDraftUrl?: string
  wordCount?: number
  aiModel?: string
  aiConfidence?: number
  researchNotes?: string
}

export interface Item {
  uniqueKey: string
  stage: Action
  category?: string
  assigneeUserId?: number
  assigneeEmail?: string
  contentText?: string
  contentUrl?: string
  wordCount?: number
  searchKeywords?: string
  searchVolume?: number
  revisionNumber: number
  lastComment?: string
  lastActorEmail?: string
  createdAt?: string
  updatedAt?: string
  history: WorkflowEvent[]
  seed: SeedRow | null
}

export function canApprove(user: User) { return ['admin', 'approver'].includes(user.role) }
export function canWrite(user: User)   { return ['admin', 'approver', 'writer'].includes(user.role) }
export function isAdmin(user: User)    { return user.role === 'admin' }

export function initials(user: User) {
  const parts = user.username.replace(/\./g, ' ').split(' ').filter(Boolean)
  return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase() || user.email.slice(0, 2).toUpperCase()
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const get = <T,>(path: string) => api<T>(path)
export const post = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: 'POST', body: JSON.stringify(body) })

export type Provider = { provider: string; model: string; mode: string }
export type Counts = Record<string, number>

export type Bootstrap = {
  stats: Counts
  pipeline: Counts
  quality: Array<{ severity: string; title: string; detail: string; source: string }>
  rules: Array<{ rule_id: string; title: string; body: string; scope: string; severity: string; source_ref: string }>
  provider: Provider
  revision: string
}

export type ApprovalData = {
  counts: Counts
  proposals: Array<Record<string, unknown> & {
    id: string; kind: string; redacted_text: string; risk: string; confidence: number
    reporter: string; location?: string; entity_ref?: string; valid_until?: string
    agent_name: string; reasoning: string; source_ref: string; connections: string[]
  }>
  capabilities: Array<{
    id: string; title: string; reason: string; status: string; change_class: string
    entity_type: string; source_ref: string; agent_name: string; risk: string
    schema: { entity_type: string; fields: Array<{ name: string; type: string; required: boolean }> }
    sample: Record<string, unknown>; surfaces: string[]
    validation: { safe: boolean; mode: string; checks: string[]; rollback: string; surfaces: string[] }
  }>
  active_capabilities: Array<{
    id: string; entity_type: string; version: number; approved_at: string; approved_by: string
    source_proposal_id: string; title: string; risk: string
    schema: { entity_type: string; fields: Array<{ name: string; type: string; required: boolean }> }
  }>
  communications: Array<{
    ticket_id: string; message_id: string; recipient: string; body: string
    citations: string[]; context: Record<string, unknown>
  }>
}

export type AskResult = {
  headline: string; detail: string; citations: string[]; unknowns: string[]
  extras?: string[]; language: string; provider: Provider; trace: string[]
}

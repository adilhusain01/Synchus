import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, post } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { titleCase } from '@/lib/utils'
import { ErrorBlock, LoadingBlock, MetricGrid, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

type InboxData = { metrics: Record<string, number>; events: Array<Record<string, string>> }
type IntakeResult = { run_id: string; dispositions: string[]; proposal_ids: string[] }

export const Route = createFileRoute('/inbox')({ component: InboxPage })

function InboxPage() {
  const client = useQueryClient()
  const [text, setText] = useState('')
  const [actor, setActor] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const query = useQuery({ queryKey: ['inbox'], queryFn: () => get<InboxData>('/api/inbox') })
  const mutation = useMutation({
    mutationFn: () => post<IntakeResult>('/api/intake/text', { text, actor: actor || 'App worker', channel: 'web_text' }),
    onSuccess: () => { setText(''); void client.invalidateQueries({ queryKey: ['inbox'] }); void client.invalidateQueries({ queryKey: ['approvals'] }) },
  })
  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Choose a supported document first')
      const form = new FormData()
      form.append('file', file)
      form.append('actor', actor || 'Company document inbox')
      const response = await fetch('/api/intake/upload', { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Upload failed')
      return result as IntakeResult & { duplicate?: boolean }
    },
    onSuccess: () => { setFile(null); void client.invalidateQueries({ queryKey: ['inbox'] }); void client.invalidateQueries({ queryKey: ['approvals'] }) },
  })
  if (query.isLoading) return <LoadingBlock />
  if (query.error) return <ErrorBlock error={query.error} />
  const data = query.data!

  return <div className="space-y-7">
    <PageHeader icon={koboyo.inbox} eyebrow="Autonomous intake" title="Worker and company inbox" description="Every update becomes an immutable event before the agent chooses answer, log, proposal, or urgent escalation." />
    <MetricGrid items={[
      { value: data.metrics.events, label: 'Preserved events' }, { value: data.metrics.pending, label: 'Awaiting review' },
      { value: data.metrics.approved, label: 'Promoted claims' }, { value: data.metrics.channels, label: 'Active channels' },
    ]} />
    <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
      <div className="space-y-5">
        <Panel title="Typed ground update" eyebrow="Dispatcher, driver, or hub worker">
          <textarea aria-label="Ground update" name="ground-update" autoComplete="off" value={text} onChange={(event) => setText(event.target.value)} rows={6} placeholder="e.g. Kal se Lucknow to Kanpur route par Unnao bridge ke paas diversion hai…" className="w-full resize-y rounded-sm border border-[#aaa394] bg-white/70 p-4 text-sm leading-6 outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15" />
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
            <input aria-label="Reporter or role" name="reporter-role" autoComplete="off" value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Reporter or role…" className="min-h-11 min-w-0 flex-1 rounded-sm border border-[#aaa394] bg-white/70 px-3 text-sm outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15" />
            <Button onClick={() => mutation.mutate()} disabled={!text.trim() || mutation.isPending}>{mutation.isPending ? 'Reconciling…' : 'Let Agent Triage'}</Button>
          </div>
          {mutation.data ? <div className="mt-4 border-l-4 border-[#c8ff3d] bg-[#eef9d2] p-4 text-sm"><p className="font-extrabold">Agent run complete</p><p className="mt-1 text-[#58625c]">{mutation.data.dispositions.map(titleCase).join(', ')}. {mutation.data.proposal_ids.length} staged for approval.</p></div> : null}
          {mutation.error ? <div className="mt-4"><ErrorBlock error={mutation.error} /></div> : null}
        </Panel>
        <Panel title="Company documents" eyebrow="Files, sheets, exports">
          <p className="text-sm leading-6 text-[#59635d]">PDF, DOCX, XLSX, CSV, JSON, and text are fingerprinted before the agent extracts and reconciles useful claims.</p>
          <input aria-label="Company document" type="file" accept=".txt,.md,.csv,.tsv,.json,.xlsx,.pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} className="mt-4 block w-full rounded-sm border border-[#aaa394] bg-white/70 p-2 text-xs file:mr-3 file:rounded-sm file:border-0 file:bg-[#e8e3d7] file:px-3 file:py-2 file:font-bold" />
          <Button variant="outline" className="mt-3" disabled={!file || upload.isPending} onClick={() => upload.mutate()}>{upload.isPending ? 'Reading Document…' : 'Process Document'}</Button>
          {upload.data ? <p className="mt-3 text-sm font-bold text-[#526b10]">{upload.data.duplicate ? 'Already processed; no duplicate context created.' : `${upload.data.proposal_ids.length} claim(s) staged for approval.`}</p> : null}
          {upload.error ? <div className="mt-3"><ErrorBlock error={upload.error} /></div> : null}
        </Panel>
      </div>
      <Panel title="Latest preserved events" eyebrow="Automatically synchronized">
        <div className="divide-y divide-[#d7d1c3]">{data.events.length ? data.events.map((event) => <article key={event.id} className="py-4 first:pt-0">
          <div className="flex flex-wrap items-center justify-between gap-2"><StatusPill tone={event.disposition === 'urgent_escalation' ? 'critical' : event.disposition === 'stage_context' ? 'blue' : 'neutral'}>{titleCase(event.disposition)}</StatusPill><time className="font-['DM_Mono'] text-[10px] text-[#737b76]">{event.at}</time></div>
          <h3 className="mt-3 font-extrabold">{titleCase(event.event_type)}</h3><p className="mt-1 text-sm leading-6 text-[#59635d]">{event.reasoning || 'Preserved without additional model reasoning.'}</p>
          <p className="mt-2 font-['DM_Mono'] text-[10px] text-[#7b837e]">{event.channel} / {event.actor_ref} / {event.source_ref}</p>
        </article>) : <p className="text-sm text-[#69716c]">No worker events have been preserved yet.</p>}</div>
      </Panel>
    </div>
  </div>
}

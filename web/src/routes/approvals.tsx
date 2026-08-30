import { useMemo, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, post, type ApprovalData } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { titleCase } from '@/lib/utils'
import { ErrorBlock, LoadingBlock, MetricGrid, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/approvals')({ component: ApprovalsPage })

function ApprovalsPage() {
  const client = useQueryClient()
  const [queue, setQueue] = useState<'proposals' | 'communications'>('proposals')
  const [selected, setSelected] = useState('')
  const query = useQuery({ queryKey: ['approvals'], queryFn: () => get<ApprovalData>('/api/approvals') })
  const decision = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => post(path, body),
    onSuccess: () => {
      setSelected('')
      void Promise.all([
        client.invalidateQueries({ queryKey: ['approvals'] }),
        client.invalidateQueries({ queryKey: ['bootstrap'] }),
        client.invalidateQueries({ queryKey: ['audit'] }),
      ])
    },
  })
  const data = query.data
  const item = useMemo(() => {
    if (!data) return undefined
    if (queue === 'proposals') {
      return data.proposals.find((entry) => entry.id === selected) || data.proposals[0]
    }
    return data.communications.find((entry) => entry.ticket_id === selected) || data.communications[0]
  }, [data, queue, selected])
  if (query.isLoading) return <LoadingBlock />
  if (query.error) return <ErrorBlock error={query.error} />
  if (!data) return null

  return <div className="space-y-7">
    <PageHeader icon={koboyo.approvals} eyebrow="Human authority boundary" title="Approval queue" description="Agents may stage and connect evidence. People decide what becomes canonical context or leaves the company." />
    <MetricGrid items={[
      { value: data.counts.pending_proposals, label: 'Context claims waiting' },
      { value: data.counts.pending_communications, label: 'Client drafts waiting' },
      { value: data.counts.approved, label: 'Claims approved' },
      { value: data.counts.rejected, label: 'Claims rejected' },
    ]} />
    <div className="flex flex-wrap gap-2"><Button size="sm" variant={queue === 'proposals' ? 'signal' : 'outline'} onClick={() => { setQueue('proposals'); setSelected('') }}>Context Proposals</Button><Button size="sm" variant={queue === 'communications' ? 'signal' : 'outline'} onClick={() => { setQueue('communications'); setSelected('') }}>Client Communications</Button></div>
    <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr]">
      {queue === 'proposals' ? <Panel title="Agent-staged context" eyebrow={`${data.proposals.length} pending`}>
        {data.proposals.length && item && 'id' in item ? <>
          <select aria-label="Context proposal" name="context-proposal" value={(item as ApprovalData['proposals'][number]).id} onChange={(event) => setSelected(event.target.value)} className="min-h-11 w-full rounded-sm border border-[#aaa394] bg-white/70 px-3 text-sm font-bold outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15">{data.proposals.map((proposal) => <option key={proposal.id}>{proposal.id}</option>)}</select>
          {(() => { const proposal = item as ApprovalData['proposals'][number]; return <article className="mt-4 rounded-sm border border-[#d7d1c3] bg-white/45 p-5">
            <div className="flex flex-wrap items-center gap-2"><StatusPill tone={proposal.risk === 'critical' || proposal.risk === 'high' ? 'critical' : 'warning'}>{proposal.risk} risk</StatusPill><StatusPill tone="blue">{Math.round(proposal.confidence * 100)}% confidence</StatusPill><span className="font-['DM_Mono'] text-[10px] text-[#727a75]">{proposal.id}</span></div>
            <h3 className="mt-5 text-2xl font-extrabold tracking-[-.04em]">{titleCase(proposal.kind)}</h3><p className="mt-3 text-base leading-7 text-[#3f4943]">{proposal.redacted_text}</p>
            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">{[['Agent', proposal.agent_name], ['Reporter', proposal.reporter], ['Location', proposal.location || 'Not inferred'], ['Vehicle', proposal.entity_ref || 'Not inferred'], ['Expiry', proposal.valid_until || 'Durable or unknown'], ['Source', proposal.source_ref]].map(([label, value]) => <div key={label}><dt className="font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#7b837e]">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div>)}</dl>
            {proposal.reasoning ? <div className="mt-5 border-l-4 border-[#2e64f5] bg-[#dfe7f4] p-4 text-sm leading-6 text-[#2855ad]">{proposal.reasoning}</div> : null}
            {proposal.connections.length ? <div className="mt-4 flex flex-wrap gap-2">{proposal.connections.map((connection) => <span key={connection} className="max-w-full truncate rounded-sm bg-[#e8e3d7] px-2 py-1 font-['DM_Mono'] text-[10px]">{connection}</span>)}</div> : null}
            <div className="mt-6 flex flex-wrap gap-2"><Button onClick={() => decision.mutate({ path: `/api/approvals/proposals/${proposal.id}`, body: { decision: 'approve', actor: 'Operations approver' } })} disabled={decision.isPending}>Approve Into Context</Button><Button variant="danger" onClick={() => window.confirm('Reject this claim? The raw event remains in the audit ledger.') && decision.mutate({ path: `/api/approvals/proposals/${proposal.id}`, body: { decision: 'reject', actor: 'Operations approver' } })} disabled={decision.isPending}>Reject Claim</Button></div>
          </article> })()}
        </> : <p className="text-sm text-[#66706a]">Queue clear. No unreviewed context claims.</p>}
      </Panel> : <Panel title="Client communications" eyebrow={`${data.communications.length} pending`}>
        {data.communications.length && item && 'ticket_id' in item ? (() => { const draft = item as ApprovalData['communications'][number]; return <>
          <select aria-label="Client communication" name="client-communication" value={draft.ticket_id} onChange={(event) => setSelected(event.target.value)} className="min-h-11 w-full rounded-sm border border-[#aaa394] bg-white/70 px-3 text-sm font-bold outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15">{data.communications.map((entry) => <option key={entry.ticket_id}>{entry.ticket_id}</option>)}</select>
          <article className="mt-4 rounded-sm border border-[#d7d1c3] bg-white/45 p-5"><p className="font-['DM_Mono'] text-[10px] uppercase tracking-[.1em] text-[#737b76]">{draft.message_id} / To {draft.recipient}</p><p className="mt-4 break-words text-sm leading-7">{draft.body}</p><p className="mt-4 break-words font-['DM_Mono'] text-[10px] text-[#737b76]">{draft.citations.join(' / ')}</p><Button className="mt-5" onClick={() => decision.mutate({ path: `/api/approvals/communications/${draft.ticket_id}`, body: { actor: 'Operations lead' } })}>Approve Client Message</Button></article>
        </> })() : <p className="text-sm text-[#66706a]">All client drafts have been decided.</p>}
      </Panel>}
      <Panel title="Approval standard" eyebrow="Before promoting a claim"><ol className="space-y-3 text-sm leading-6 text-[#56605a]">{['Source is identifiable', 'Statement is reusable', 'Entity and location linkage is valid', 'Temporary knowledge has an expiry', 'Conflicts remain visible'].map((standard, index) => <li key={standard} className="flex gap-3"><span className="font-['DM_Mono'] text-[#17201c]">0{index + 1}</span>{standard}</li>)}</ol><div className="mt-6 border-l-4 border-[#ffcb3d] bg-[#fff4bf] p-4 text-sm leading-6 text-[#70550c]">Approval changes canonical context. Rejection preserves the raw event and audit trail.</div></Panel>
    </div>
    {decision.error ? <ErrorBlock error={decision.error} /> : null}
  </div>
}

import { useMemo, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, post, type ApprovalData } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { titleCase } from '@/lib/utils'
import { ErrorBlock, LoadingBlock, MetricGrid, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/app/approvals')({ component: ApprovalsPage })

function ApprovalsPage() {
  const client = useQueryClient()
  const [queue, setQueue] = useState<'proposals' | 'capabilities' | 'communications'>('proposals')
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
    if (queue === 'capabilities') {
      const capabilities = data.capabilities || []
      return capabilities.find((entry) => entry.id === selected) || capabilities[0]
    }
    return data.communications.find((entry) => entry.ticket_id === selected) || data.communications[0]
  }, [data, queue, selected])
  if (query.isLoading) return <LoadingBlock />
  if (query.error) return <ErrorBlock error={query.error} />
  if (!data) return null
  const capabilities = data.capabilities || []
  const activeCapabilities = data.active_capabilities || []

  return <div className="space-y-7">
    <PageHeader icon={koboyo.approvals} eyebrow="Human authority boundary" title="Approval queue" description="Agents may stage and connect evidence. People decide what becomes canonical context or leaves the company." />
    <MetricGrid items={[
      { value: data.counts.pending_proposals, label: 'Context claims waiting' },
      { value: data.counts.pending_capabilities ?? capabilities.length, label: 'Capabilities waiting' },
      { value: data.counts.pending_communications, label: 'Client drafts waiting' },
      { value: data.counts.approved, label: 'Claims approved' },
      { value: data.counts.rejected, label: 'Claims rejected' },
    ]} />
    <div className="flex flex-wrap gap-2"><Button size="sm" variant={queue === 'proposals' ? 'signal' : 'outline'} onClick={() => { setQueue('proposals'); setSelected('') }}>Context Proposals</Button><Button size="sm" variant={queue === 'capabilities' ? 'signal' : 'outline'} onClick={() => { setQueue('capabilities'); setSelected('') }}>Capability Lab</Button><Button size="sm" variant={queue === 'communications' ? 'signal' : 'outline'} onClick={() => { setQueue('communications'); setSelected('') }}>Client Communications</Button></div>
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
      </Panel> : queue === 'capabilities' ? <Panel title="Capability Lab" eyebrow={`${capabilities.length} pending`}>
        {capabilities.length && item && 'schema' in item ? (() => { const capability = item as ApprovalData['capabilities'][number]; return <>
          <select aria-label="Capability proposal" name="capability-proposal" value={capability.id} onChange={(event) => setSelected(event.target.value)} className="min-h-11 w-full rounded-sm border border-[#aaa394] bg-white/70 px-3 text-sm font-bold outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15">{capabilities.map((entry) => <option key={entry.id}>{entry.id}</option>)}</select>
          <article className="mt-4 overflow-hidden rounded-xl border border-[#c9c2b3] bg-[#fffaf0] shadow-[0_12px_35px_rgba(33,45,38,.08)]">
            <header className="bg-[#e8f0df] p-5"><div className="flex flex-wrap items-center gap-2"><StatusPill tone={capability.risk === 'high' || capability.risk === 'critical' ? 'critical' : 'warning'}>{capability.risk} risk</StatusPill><StatusPill tone="blue">{titleCase(capability.change_class)}</StatusPill><span className="font-['DM_Mono'] text-[10px] text-[#68716b]">{capability.id}</span></div><h3 className="mt-4 text-2xl font-extrabold tracking-[-.04em]">{capability.title}</h3><p className="mt-2 text-sm leading-6 text-[#4e5b53]">{capability.reason}</p></header>
            <div className="grid gap-5 p-5 lg:grid-cols-2"><section><p className="font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#6c756f]">Proposed entity</p><p className="mt-2 font-extrabold">{capability.entity_type}</p><div className="mt-3 flex flex-wrap gap-2">{capability.schema.fields.map((field) => <span key={field.name} className="rounded-full border border-[#c9c2b3] bg-[#f5efdF] px-3 py-1.5 font-['DM_Mono'] text-[10px]">{field.name}: {field.type}{field.required ? ' required' : ''}</span>)}</div></section><section><p className="font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#6c756f]">Affected surfaces</p><div className="mt-3 flex flex-wrap gap-2">{capability.surfaces.map((surface) => <span key={surface} className="rounded-full bg-[#dfe7f4] px-3 py-1.5 text-xs font-bold text-[#2855ad]">{titleCase(surface)}</span>)}</div><p className="mt-4 font-['DM_Mono'] text-[10px] text-[#6c756f]">Source / {capability.source_ref}</p></section></div>
            <section className="border-t border-[#d8d1c3] bg-[#fff4bf]/55 p-5"><p className="font-extrabold">Safety contract</p><ul className="mt-2 grid gap-1 text-xs leading-5 text-[#65551e] sm:grid-cols-2">{capability.validation.checks.map((check) => <li key={check}>{check}</li>)}</ul><p className="mt-3 text-xs leading-5 text-[#65551e]">Rollback: {capability.validation.rollback}</p></section>
            <div className="flex flex-wrap gap-2 p-5"><Button onClick={() => decision.mutate({ path: `/api/approvals/capabilities/${capability.id}`, body: { decision: 'approve', actor: 'Capability approver' } })} disabled={decision.isPending}>Register Capability</Button><Button variant="danger" onClick={() => window.confirm('Reject this capability? The source event and held data will remain auditable.') && decision.mutate({ path: `/api/approvals/capabilities/${capability.id}`, body: { decision: 'reject', actor: 'Capability approver' } })} disabled={decision.isPending}>Reject Proposal</Button></div>
          </article>
        </> })() : <p className="text-sm text-[#66706a]">No unsupported data shapes are waiting for review.</p>}
        {activeCapabilities.length ? <section className="mt-6 border-t-2 border-[#17201c] pt-5"><h3 className="font-extrabold">Active capabilities</h3><div className="mt-3 space-y-3">{activeCapabilities.map((capability) => <article key={capability.id} className="flex flex-col gap-3 rounded-xl border border-[#c9c2b3] bg-[#e8f0df] p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-extrabold">{capability.title}</p><p className="mt-1 font-['DM_Mono'] text-[10px] text-[#657069]">{capability.entity_type} / v{capability.version} / approved by {capability.approved_by}</p></div><Button size="sm" variant="outline" onClick={() => window.confirm('Roll back this capability? Its records will return to held state; evidence will not be deleted.') && decision.mutate({ path: `/api/approvals/capabilities/${capability.source_proposal_id}/rollback`, body: { actor: 'Capability approver' } })}>Roll Back</Button></article>)}</div></section> : null}
      </Panel> : <Panel title="Client communications" eyebrow={`${data.communications.length} pending`}>
        {data.communications.length && item && 'ticket_id' in item ? (() => { const draft = item as ApprovalData['communications'][number]; return <>
          <select aria-label="Client communication" name="client-communication" value={draft.ticket_id} onChange={(event) => setSelected(event.target.value)} className="min-h-11 w-full rounded-sm border border-[#aaa394] bg-white/70 px-3 text-sm font-bold outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15">{data.communications.map((entry) => <option key={entry.ticket_id}>{entry.ticket_id}</option>)}</select>
          <article className="mt-4 rounded-sm border border-[#d7d1c3] bg-white/45 p-5"><p className="font-['DM_Mono'] text-[10px] uppercase tracking-[.1em] text-[#737b76]">{draft.message_id} / To {draft.recipient}</p><p className="mt-4 break-words text-sm leading-7">{draft.body}</p><p className="mt-4 break-words font-['DM_Mono'] text-[10px] text-[#737b76]">{draft.citations.join(' / ')}</p><Button className="mt-5" onClick={() => decision.mutate({ path: `/api/approvals/communications/${draft.ticket_id}`, body: { actor: 'Operations lead' } })}>Approve Client Message</Button></article>
        </> })() : <p className="text-sm text-[#66706a]">All client drafts have been decided.</p>}
      </Panel>}
      <Panel title={queue === 'capabilities' ? 'Capability standard' : 'Approval standard'} eyebrow={queue === 'capabilities' ? 'Before extending Synchus' : 'Before promoting a claim'}><ol className="space-y-3 text-sm leading-6 text-[#56605a]">{(queue === 'capabilities' ? ['Ordinary context is insufficient', 'Change is additive and typed', 'Affected surfaces are explicit', 'No arbitrary code executes', 'Rollback preserves evidence'] : ['Source is identifiable', 'Statement is reusable', 'Entity and location linkage is valid', 'Temporary knowledge has an expiry', 'Conflicts remain visible']).map((standard, index) => <li key={standard} className="flex gap-3"><span className="font-['DM_Mono'] text-[#17201c]">0{index + 1}</span>{standard}</li>)}</ol><div className="mt-6 border-l-4 border-[#ffcb3d] bg-[#fff4bf] p-4 text-sm leading-6 text-[#70550c]">{queue === 'capabilities' ? 'Approval registers a reversible schema capability. Bespoke code still requires an isolated build and test promotion.' : 'Approval changes canonical context. Rejection preserves the raw event and audit trail.'}</div></Panel>
    </div>
    {decision.error ? <ErrorBlock error={decision.error} /> : null}
  </div>
}

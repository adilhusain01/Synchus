import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { get } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { titleCase } from '@/lib/utils'
import { ErrorBlock, LoadingBlock, MetricGrid, PageHeader, Panel } from '@/components/common'
import { Button } from '@/components/ui/button'

type AuditData = { ledger: string; rows: Array<Record<string, unknown>>; counts: Record<string, number> }
const ledgers = ['runs', 'events', 'sources', 'decisions', 'quarantine'] as const

export const Route = createFileRoute('/audit')({ component: AuditPage })

function AuditPage() {
  const [ledger, setLedger] = useState<(typeof ledgers)[number]>('runs')
  const query = useQuery({ queryKey: ['audit', ledger], queryFn: () => get<AuditData>(`/api/audit/${ledger}`) })
  if (query.isLoading) return <LoadingBlock label="Opening ledger" />
  if (query.error) return <ErrorBlock error={query.error} />
  const data = query.data!
  const columns = data.rows.length ? Object.keys(data.rows[0]) : []
  return <div className="space-y-7">
    <PageHeader icon={koboyo.audit} eyebrow="Provenance and agent trace" title="Audit ledger" description="Raw inputs, proposed facts, human decisions, sources, and model or tool runs stay separate and inspectable." />
    <MetricGrid items={[{ value: data.counts.runs, label: 'Agent runs' }, { value: data.counts.events, label: 'Intake events' }, { value: data.counts.sources, label: 'Source files' }, { value: data.counts.quarantine, label: 'Quarantined records' }]} />
    <div className="flex flex-wrap gap-2">{ledgers.map((item) => <Button key={item} size="sm" variant={ledger === item ? 'signal' : 'outline'} onClick={() => setLedger(item)}>{titleCase(item)}</Button>)}</div>
    <Panel title={titleCase(ledger)} eyebrow={`${data.rows.length} records shown`}>
      <div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[760px] border-collapse text-left text-xs"><thead><tr className="border-b-2 border-[#17201c]">{columns.map((column) => <th key={column} className="px-3 py-3 font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#68716b]">{titleCase(column)}</th>)}</tr></thead><tbody>{data.rows.map((row, index) => <tr key={index} className="border-b border-[#d7d1c3] align-top">{columns.map((column) => <td key={column} className="max-w-[380px] px-3 py-3 leading-5 text-[#46504a]"><span className="line-clamp-4 break-words">{typeof row[column] === 'string' ? row[column] : JSON.stringify(row[column])}</span></td>)}</tr>)}</tbody></table></div>
      <div className="space-y-3 md:hidden">{data.rows.map((row, index) => <article key={index} className="rounded-sm border border-[#d7d1c3] bg-white/45 p-4">{columns.map((column) => <div key={column} className="grid grid-cols-[7rem_1fr] gap-3 border-b border-[#e3ded3] py-2 last:border-0"><span className="font-['DM_Mono'] text-[9px] uppercase tracking-[.08em] text-[#737b76]">{titleCase(column)}</span><span className="break-words text-xs text-[#46504a]">{typeof row[column] === 'string' ? row[column] : JSON.stringify(row[column])}</span></div>)}</article>)}</div>
    </Panel>
  </div>
}

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { get, type Bootstrap } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { ErrorBlock, LoadingBlock, MetricGrid, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/control')({ component: ControlRoom })

function ControlRoom() {
  const [severity, setSeverity] = useState<'critical' | 'warning' | 'all'>('critical')
  const query = useQuery({ queryKey: ['bootstrap'], queryFn: () => get<Bootstrap>('/api/bootstrap') })
  if (query.isLoading) return <LoadingBlock />
  if (query.error) return <ErrorBlock error={query.error} />
  const data = query.data!
  const issues = severity === 'all' ? data.quality : data.quality.filter((item) => item.severity === severity)
  const decisions = data.stats.pending + data.pipeline.communications

  return <div className="space-y-7">
    <PageHeader icon={koboyo.control} eyebrow="Active operational intelligence" title="Control room" description="Exceptions first: bad data, conflicting evidence, and approved rules that can stop work." />
    <MetricGrid items={[
      { value: data.stats.vehicles, label: 'Canonical vehicles' },
      { value: data.stats.trips, label: 'Historical trips' },
      { value: data.stats.rules, label: 'Approved rules' },
      { value: decisions, label: 'Human decisions queued' },
    ]} />
    <div className="grid gap-6 xl:grid-cols-[1.25fr_.75fr]">
      <Panel title="Action queue" eyebrow={`${issues.length} visible conditions`} action={<div className="flex flex-wrap gap-1.5">{(['critical', 'warning', 'all'] as const).map((item) => <Button key={item} size="sm" variant={severity === item ? 'signal' : 'outline'} onClick={() => setSeverity(item)}>{item === 'all' ? 'Everything' : item === 'warning' ? 'Warnings' : 'Critical'}</Button>)}</div>}>
        <div className="space-y-3">
          {issues.map((issue) => <article key={issue.title} className={`border-l-4 bg-white/55 p-4 ${issue.severity === 'critical' ? 'border-[#ff5c35]' : issue.severity === 'warning' ? 'border-[#dca91c]' : 'border-[#2e64f5]'}`}>
            <div className="flex flex-wrap items-start justify-between gap-3"><h3 className="font-extrabold tracking-[-.02em]">{issue.title}</h3><StatusPill tone={issue.severity === 'critical' ? 'critical' : issue.severity === 'warning' ? 'warning' : 'blue'}>{issue.severity}</StatusPill></div>
            <p className="mt-2 text-sm leading-6 text-[#59635d]">{issue.detail}</p>
            <p className="mt-3 font-['DM_Mono'] text-[10px] uppercase tracking-[.1em] text-[#7c837e]">Source / {issue.source}</p>
          </article>)}
        </div>
      </Panel>
      <Panel title="Dispatch guardrails" eyebrow="Approved critical rules">
        <div className="divide-y divide-[#d7d1c3]">{data.rules.filter((rule) => rule.severity === 'critical').slice(0, 5).map((rule) => <details key={rule.rule_id} className="group py-4 first:pt-0">
          <summary className="cursor-pointer list-none text-sm font-extrabold outline-none focus-visible:ring-2 focus-visible:ring-[#2e64f5]">{rule.scope.toUpperCase()} / {rule.title}</summary>
          <p className="mt-3 text-sm leading-6 text-[#59635d]">{rule.body}</p><p className="mt-2 font-['DM_Mono'] text-[10px] text-[#7c837e]">{rule.source_ref}</p>
        </details>)}</div>
      </Panel>
    </div>
  </div>
}

import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { post, type AskResult } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { ErrorBlock, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/app/ask')({ component: AskPage })

function AskPage() {
  const [question, setQuestion] = useState('')
  const mutation = useMutation({ mutationFn: (value: string) => post<AskResult>('/api/ask', { question: value }) })
  const submit = () => question.trim() && mutation.mutate(question.trim())

  return <div className="space-y-7">
    <PageHeader icon={koboyo.ask} title="Ask Synchus" actions={<Button asChild variant="signal" size="sm"><Link to="/">Start Live Voice</Link></Button>} />
    <div className="max-w-6xl space-y-5">
        <Panel title="Written query">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input aria-label="Operational question" name="operational-question" autoComplete="off" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && submit()} placeholder="e.g. Kya DL30AN8381 ko winter mein Delhi bhej sakte hain?…" className="min-h-12 min-w-0 flex-1 rounded-sm border border-[#aaa394] bg-white/70 px-4 text-sm outline-none transition-[border-color,box-shadow] focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15" />
            <Button onClick={submit} disabled={!question.trim() || mutation.isPending} className="sm:min-w-44">{mutation.isPending ? 'Reasoning…' : 'Reason Over Context'}</Button>
          </div>
          {mutation.error ? <div className="mt-4"><ErrorBlock error={mutation.error} /></div> : null}
        </Panel>
        {mutation.data ? <article aria-live="polite" className="rounded-sm bg-[#17201c] p-6 text-[#f7f4ea] shadow-[7px_7px_0_#c8ff3d] sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3"><p className="font-['DM_Mono'] text-[10px] uppercase tracking-[.12em] text-[#bfc8c3]">Answer / {mutation.data.provider.provider}</p><StatusPill tone="good">{mutation.data.language}</StatusPill></div>
          <h2 className="mt-5 max-w-4xl text-[clamp(1.5rem,3vw,2.5rem)] font-extrabold leading-[1.05] tracking-[-.05em]">{mutation.data.headline}</h2>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-[#d6ddd9]">{mutation.data.detail}</p>
          <div className="mt-6 flex flex-wrap gap-2">{mutation.data.citations.map((citation) => <span key={citation} className="rounded-sm border border-[#526058] bg-[#303b35] px-2.5 py-1 font-['DM_Mono'] text-[10px] text-[#e7ece9]">{citation}</span>)}</div>
          {mutation.data.unknowns.length ? <div className="mt-6 grid gap-2">{mutation.data.unknowns.map((unknown) => <div key={unknown} className="border-l-2 border-[#ffcb3d] bg-white/5 px-3 py-2 font-['DM_Mono'] text-xs text-[#f0db99]">Unknown / {unknown}</div>)}</div> : null}
        </article> : null}
    </div>
  </div>
}

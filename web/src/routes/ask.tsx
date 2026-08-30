import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { post, type AskResult } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { ErrorBlock, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/ask')({ component: AskPage })

const examples = ['RJ43DD3546 Orion ke liye eligible hai?', 'Shakti ka real SLA kitna hai?', 'Breakdown origin se 40 km hai; replacement kahan se aaye?']

function AskPage() {
  const [question, setQuestion] = useState('')
  const mutation = useMutation({ mutationFn: (value: string) => post<AskResult>('/api/ask', { question: value }) })
  const submit = () => question.trim() && mutation.mutate(question.trim())

  return <div className="space-y-7">
    <PageHeader icon={koboyo.ask} eyebrow="Grounded multilingual reasoning" title="Ask Meridian" description="Ask naturally in Hindi, Hinglish, or English. The answer separates evidence, useful inference, and missing live state." />
    <div className="grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
      <div className="space-y-5">
        <Panel title="What do you need to know?" eyebrow="Operational question">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input aria-label="Operational question" name="operational-question" autoComplete="off" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && submit()} placeholder="e.g. Kya DL30AN8381 ko winter mein Delhi bhej sakte hain?…" className="min-h-12 min-w-0 flex-1 rounded-sm border border-[#aaa394] bg-white/70 px-4 text-sm outline-none transition-[border-color,box-shadow] focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15" />
            <Button onClick={submit} disabled={!question.trim() || mutation.isPending} className="sm:min-w-44">{mutation.isPending ? 'Reasoning…' : 'Reason Over Context'}</Button>
          </div>
          {mutation.error ? <div className="mt-4"><ErrorBlock error={mutation.error} /></div> : null}
        </Panel>
        {mutation.data ? <article aria-live="polite" className="rounded-sm bg-[#17201c] p-6 text-[#f7f4ea] shadow-[9px_9px_0_#c8ff3d] sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3"><p className="font-['DM_Mono'] text-[10px] uppercase tracking-[.12em] text-[#bfc8c3]">Answer / {mutation.data.provider.provider}</p><StatusPill tone="good">{mutation.data.language}</StatusPill></div>
          <h2 className="mt-5 max-w-4xl text-[clamp(1.5rem,3vw,2.5rem)] font-extrabold leading-[1.05] tracking-[-.05em]">{mutation.data.headline}</h2>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-[#d6ddd9]">{mutation.data.detail}</p>
          <div className="mt-6 flex flex-wrap gap-2">{mutation.data.citations.map((citation) => <span key={citation} className="rounded-sm border border-[#526058] bg-[#303b35] px-2.5 py-1 font-['DM_Mono'] text-[10px] text-[#e7ece9]">{citation}</span>)}</div>
          {mutation.data.unknowns.length ? <div className="mt-6 grid gap-2">{mutation.data.unknowns.map((unknown) => <div key={unknown} className="border-l-2 border-[#ffcb3d] bg-white/5 px-3 py-2 font-['DM_Mono'] text-xs text-[#f0db99]">Unknown / {unknown}</div>)}</div> : null}
        </article> : <div className="border-l-4 border-[#2e64f5] bg-[#dfe7f4] p-4 text-sm text-[#2855ad]">Ask a question or choose a field scenario. Meridian will retrieve, reconcile, reason, cite, and surface unknowns.</div>}
      </div>
      <div className="space-y-5">
        <Panel title="Try a field question" eyebrow="Scenario shortcuts"><div className="flex flex-wrap gap-2">{examples.map((example) => <Button key={example} variant="outline" size="sm" className="h-auto min-h-10 max-w-full justify-start whitespace-normal text-left" onClick={() => setQuestion(example)}>{example}</Button>)}</div></Panel>
        <Panel title="Answer contract"><ol className="space-y-2 text-sm text-[#58625c]">{['Retrieve bounded evidence', 'Reconcile conflicts', 'Reason conservatively', 'Cite sources', 'Surface unknowns'].map((item, index) => <li key={item} className="flex gap-3"><span className="font-['DM_Mono'] text-[#17201c]">0{index + 1}</span>{item}</li>)}</ol></Panel>
      </div>
    </div>
  </div>
}

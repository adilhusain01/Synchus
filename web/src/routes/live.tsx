import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { get, type Provider } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { ErrorBlock, LoadingBlock, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

type LiveStatus = { voice_ready: boolean; telegram_ready: boolean; voice_url: string; provider: Provider }

export const Route = createFileRoute('/live')({ component: LivePage })

function LivePage() {
  const query = useQuery({ queryKey: ['live-status'], queryFn: () => get<LiveStatus>('/api/live/status') })
  if (query.isLoading) return <LoadingBlock />
  if (query.error) return <ErrorBlock error={query.error} />
  const data = query.data!
  return <div className="space-y-7">
    <PageHeader icon={koboyo.live} eyebrow="Full duplex operational voice" title="Meridian Live" description="A fluid, interruptible voice agent with the same bounded context tools and approval boundary as every other channel." actions={<StatusPill tone={data.voice_ready ? 'good' : 'warning'}>{data.voice_ready ? 'Voice ready' : 'Model key required'}</StatusPill>} />
    <div className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
      <section className="relative grid min-h-[540px] place-items-center overflow-hidden rounded-sm border border-[#283029] bg-[#050706]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_55%,rgba(80,105,245,.18),transparent_38%)]" />
        <div className="relative aspect-square w-[min(64vw,330px)] rounded-full bg-[radial-gradient(circle_at_36%_30%,#ffffff_0_7%,#d5dcff_23%,#7892ff_50%,#4053bc_72%,#17224f_100%)] shadow-[0_0_100px_rgba(120,152,255,.42),inset_-34px_-28px_70px_rgba(16,27,91,.55)] motion-safe:animate-[pulse_3.8s_ease-in-out_infinite]" />
        <div className="absolute inset-x-0 bottom-7 text-center font-['DM_Mono'] text-[10px] uppercase tracking-[.14em] text-[#b9c3bd]">Persistent session / interruption / grounded tools</div>
      </section>
      <div className="space-y-5">
        <Panel title="Browser voice" eyebrow={`${data.provider.provider} / ${data.provider.model}`}><p className="text-sm leading-6 text-[#59635d]">Speak naturally in Hindi, Hinglish, or English. The agent can search context, inspect vehicles and routes, answer, or stage an observation for human approval.</p><Button asChild className="mt-5"><a href={data.voice_url} target="_blank" rel="noreferrer">Open Voice Conversation</a></Button></Panel>
        <Panel title="Telegram field gateway" eyebrow={data.telegram_ready ? 'Configured' : 'Awaiting bot token'}><p className="text-sm leading-6 text-[#59635d]">Workers can send text, voice notes, and supported documents. Inputs are redacted, logged, reasoned over, and staged only when useful.</p><div className="mt-4"><StatusPill tone={data.telegram_ready ? 'good' : 'neutral'}>{data.telegram_ready ? 'Gateway ready' : 'Not connected'}</StatusPill></div></Panel>
        <div className="border-l-4 border-[#ffcb3d] bg-[#fff4bf] p-4 text-sm leading-6 text-[#70550c]">Telegram is a field channel, not the system of record. Identity allowlists and human promotion remain required.</div>
      </div>
    </div>
  </div>
}

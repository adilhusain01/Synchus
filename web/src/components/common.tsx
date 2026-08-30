import type { ReactNode } from 'react'
import { cn, formatNumber } from '@/lib/utils'

export function KoboyoIcon({ src, alt = '', className }: { src: string; alt?: string; className?: string }) {
  return <img src={src} alt={alt} width={40} height={40} aria-hidden={alt ? undefined : true} className={cn('size-10 object-contain', className)} />
}

export function PageHeader({ icon, eyebrow, title, description, actions }: {
  icon: string; eyebrow: string; title: string; description: string; actions?: ReactNode
}) {
  return (
    <header className="flex flex-col gap-5 border-b border-[#d7d1c3] pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 items-start gap-4">
        <div className="grid size-14 shrink-0 place-items-center rounded-sm border border-[#c9c2b3] bg-[#fffaf0]">
          <KoboyoIcon src={icon} className="size-11" />
        </div>
        <div className="min-w-0">
          <p className="font-['DM_Mono'] text-[11px] uppercase tracking-[0.13em] text-[#69716c]">{eyebrow}</p>
          <h1 className="mt-1 text-pretty text-[clamp(1.7rem,3vw,2.8rem)] font-extrabold leading-[.98] tracking-[-.055em] text-[#17201c]">{title}</h1>
          <p className="mt-2 max-w-3xl text-pretty text-sm leading-6 text-[#56605a]">{description}</p>
        </div>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  )
}

export function MetricGrid({ items }: { items: Array<{ label: string; value: number | string; note?: string }> }) {
  return (
    <section className="grid grid-cols-2 gap-x-5 gap-y-4 xl:grid-cols-4">
      {items.map((item) => (
        <article key={item.label} className="border-t-[3px] border-[#17201c] pt-3">
          <p className="text-[clamp(1.8rem,4vw,3.2rem)] font-extrabold leading-none tracking-[-.07em] text-[#17201c] tabular-nums">{typeof item.value === 'number' ? formatNumber(item.value) : item.value}</p>
          <p className="mt-3 font-['DM_Mono'] text-[10px] uppercase tracking-[0.1em] text-[#657069]">{item.label}</p>
          {item.note ? <p className="mt-1 text-xs text-[#737a75]">{item.note}</p> : null}
        </article>
      ))}
    </section>
  )
}

export function Panel({ title, eyebrow, children, className, action }: { title?: string; eyebrow?: string; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <section className={cn('rounded-sm border border-[#d7d1c3] bg-[#fffaf0]/65 p-5', className)}>
      {title || action ? <div className="mb-4 flex items-start justify-between gap-3"><div>{eyebrow ? <p className="font-['DM_Mono'] text-[10px] uppercase tracking-[.12em] text-[#747b76]">{eyebrow}</p> : null}{title ? <h2 className="mt-1 text-xl font-extrabold tracking-[-.035em] text-[#17201c]">{title}</h2> : null}</div>{action}</div> : null}
      {children}
    </section>
  )
}

export function StatusPill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'critical' | 'warning' | 'good' | 'blue' }) {
  const tones = { neutral: 'border-[#aaa394] bg-[#e8e3d7] text-[#505853]', critical: 'border-[#ff5c35]/50 bg-[#ff5c35]/10 text-[#ad351d]', warning: 'border-[#d8a013]/50 bg-[#ffe98f]/35 text-[#8a6510]', good: 'border-[#7ca611]/45 bg-[#c8ff3d]/25 text-[#46620a]', blue: 'border-[#2e64f5]/35 bg-[#2e64f5]/10 text-[#214bb7]' }
  return <span className={cn("inline-flex w-fit rounded-full border px-2.5 py-1 font-['DM_Mono'] text-[10px] uppercase tracking-[.08em]", tones[tone])}>{children}</span>
}

export function LoadingBlock({ label = 'Loading context' }: { label?: string }) {
  return <div role="status" aria-live="polite" className="grid min-h-48 place-items-center rounded-sm border border-dashed border-[#b8b0a1] bg-white/25 font-['DM_Mono'] text-xs uppercase tracking-[.12em] text-[#6c746e]">{label}…</div>
}

export function ErrorBlock({ error }: { error: Error }) {
  return <div role="alert" className="border-l-4 border-[#ff5c35] bg-[#fffaf0] p-4 text-sm text-[#8d2d1a]">{error.message}</div>
}

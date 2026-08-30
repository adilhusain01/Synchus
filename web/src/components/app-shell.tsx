import { useEffect } from 'react'
import { Link, Outlet } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, type Bootstrap } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { KoboyoIcon } from '@/components/common'

const destinations = [
  { to: '/control', label: 'Control Room', icon: koboyo.control },
  { to: '/route', label: 'Route', icon: koboyo.route },
  { to: '/ask', label: 'Ask', icon: koboyo.ask },
  { to: '/inbox', label: 'Inbox', icon: koboyo.inbox },
  { to: '/live', label: 'Live', icon: koboyo.live },
  { to: '/approvals', label: 'Approvals', icon: koboyo.approvals },
  { to: '/audit', label: 'Audit', icon: koboyo.audit },
] as const

function ContextSync() {
  const client = useQueryClient()
  useEffect(() => {
    const events = new EventSource('/api/events')
    events.addEventListener('context', () => { void client.invalidateQueries() })
    return () => events.close()
  }, [client])
  return null
}

export function AppShell() {
  const compact = useUiStore((state) => state.compactRail)
  const setCompact = useUiStore((state) => state.setCompactRail)
  const bootstrap = useQuery({ queryKey: ['bootstrap'], queryFn: () => get<Bootstrap>('/api/bootstrap') })

  return (
    <div className="min-h-dvh overflow-x-hidden bg-[#f2efe6] font-['Manrope_Variable'] text-[#17201c] antialiased selection:bg-[#c8ff3d]">
      <ContextSync />
      <a href="#main-content" className="fixed left-3 top-3 z-50 -translate-y-20 rounded-sm bg-[#c8ff3d] px-4 py-2 text-sm font-extrabold text-[#17201c] transition-transform focus-visible:translate-y-0 focus-visible:ring-3 focus-visible:ring-[#2e64f5]">Skip to Content</a>
      <aside className={cn('fixed inset-y-0 left-0 z-30 flex w-[76px] flex-col border-r border-[#344039] bg-[#17201c] text-[#f7f4ea] transition-[width] duration-200 ease-[cubic-bezier(.23,1,.32,1)] lg:w-[248px]', compact && 'lg:w-[84px]')}>
        <div className="flex h-24 items-center gap-3 border-b border-[#344039] px-3 lg:px-5">
          <div className="grid size-12 shrink-0 place-items-center rounded-sm bg-[#f7f4ea]"><KoboyoIcon src={koboyo.brand} className="size-10" /></div>
          <div className={cn('hidden min-w-0 lg:block', compact && 'lg:hidden')}>
            <p className="text-lg font-extrabold tracking-[-.05em]">MERIDIAN</p>
          </div>
        </div>

        <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 overflow-y-auto p-2 lg:p-3">
          {destinations.map((item) => (
            <Link key={item.to} to={item.to} activeOptions={{ exact: true }}
              className={cn('group flex min-h-14 items-center justify-center gap-3 rounded-sm border border-transparent px-2 text-xs font-bold text-[#c8cfcb] outline-none transition-[background-color,color,border-color,transform] duration-150 ease-[cubic-bezier(.23,1,.32,1)] active:scale-[.98] focus-visible:ring-2 focus-visible:ring-[#c8ff3d] lg:justify-start lg:px-3', compact && 'lg:justify-center lg:px-2')}
              activeProps={{ className: 'border-[#c8ff3d]/35 bg-[#c8ff3d] !text-[#17201c]' }}>
              <span className="grid size-9 shrink-0 place-items-center rounded-sm bg-[#f7f4ea]"><KoboyoIcon src={item.icon} className="size-8" /></span>
              <span className={cn('hidden lg:block', compact && 'lg:hidden')}>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="border-t border-[#344039] p-3">
          <div className={cn('hidden lg:block', compact && 'lg:hidden')}>
            <div className="flex items-center gap-2 font-['DM_Mono'] text-[9px] uppercase tracking-[.11em] text-[#b8c2bc]"><span className="size-2 rounded-full bg-[#c8ff3d] shadow-[0_0_0_4px_rgba(200,255,61,.12)]" />Context synchronized</div>
            <p className="mt-2 truncate text-xs text-[#87928c]">{bootstrap.data?.provider.provider || 'Connecting'} / {bootstrap.data?.provider.model || 'context API'}</p>
          </div>
          <Button variant="outline" size="sm" className="mt-3 hidden w-full border-[#59665f] text-[#e7ece9] hover:bg-[#29362f] hover:text-white lg:inline-flex" onClick={() => setCompact(!compact)}>{compact ? 'Expand Rail' : 'Compact Rail'}</Button>
        </div>
      </aside>

      <main id="main-content" className={cn('min-h-dvh pl-[76px] transition-[padding] duration-200 ease-[cubic-bezier(.23,1,.32,1)] lg:pl-[248px]', compact && 'lg:pl-[84px]')}>
        <div className="mx-auto w-full max-w-[1680px] p-4 sm:p-6 lg:p-8 xl:p-10"><Outlet /></div>
      </main>
    </div>
  )
}

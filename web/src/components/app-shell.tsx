import { useEffect, useState } from 'react'
import { Link, Outlet } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { koboyo } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { KoboyoIcon } from '@/components/common'

const destinations = [
  { to: '/app/control', label: 'Control Room', icon: koboyo.control },
  { to: '/app/route', label: 'Route', icon: koboyo.route },
  { to: '/app/ask', label: 'Ask', icon: koboyo.ask },
  { to: '/app/inbox', label: 'Inbox', icon: koboyo.inbox },
  { to: '/app/approvals', label: 'Approvals', icon: koboyo.approvals },
  { to: '/app/audit', label: 'Audit', icon: koboyo.audit },
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
  const [railOpen, setRailOpen] = useState(false)

  return (
    <div className="min-h-dvh overflow-x-hidden bg-[#f2efe6] font-['Manrope_Variable'] text-[#17201c] antialiased selection:bg-[#c8ff3d]">
      <ContextSync />
      <a href="#main-content" className="fixed left-3 top-3 z-50 -translate-y-20 rounded-sm bg-[#c8ff3d] px-4 py-2 text-sm font-extrabold text-[#17201c] transition-transform focus-visible:translate-y-0 focus-visible:ring-3 focus-visible:ring-[#2e64f5]">Skip to Content</a>
      <aside
        onPointerEnter={(event) => event.pointerType === 'mouse' && setRailOpen(true)}
        onPointerLeave={(event) => event.pointerType === 'mouse' && setRailOpen(false)}
        onFocus={() => setRailOpen(true)}
        onBlur={(event) => !event.currentTarget.contains(event.relatedTarget) && setRailOpen(false)}
        className={cn('fixed inset-y-0 left-0 z-30 flex w-[72px] flex-col overflow-hidden border-r border-[#344039] bg-[#17201c] text-[#f7f4ea] shadow-[10px_0_28px_rgba(23,32,28,0)] transition-[width,box-shadow] duration-150 ease-[cubic-bezier(.23,1,.32,1)]', railOpen && 'w-[220px] shadow-[10px_0_28px_rgba(23,32,28,.18)]')}
      >
        <div className="flex h-20 items-center gap-3 border-b border-[#344039] px-3">
          <div className="grid size-11 shrink-0 place-items-center rounded-sm bg-[#f7f4ea]"><KoboyoIcon src={koboyo.brand} className="size-9" /></div>
          <p className={cn('whitespace-nowrap text-base font-extrabold tracking-[-.04em] opacity-0 transition-opacity duration-100', railOpen && 'opacity-100')}>SYNCHUS</p>
        </div>

        <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
          {destinations.map((item) => (
            <Link key={item.to} to={item.to} activeOptions={{ exact: true }}
              className="group flex min-h-12 items-center gap-3 rounded-sm border border-transparent px-2 text-xs font-bold text-[#c8cfcb] outline-none transition-[background-color,color,border-color,transform] duration-150 ease-[cubic-bezier(.23,1,.32,1)] active:scale-[.98] focus-visible:ring-2 focus-visible:ring-[#c8ff3d]"
              activeProps={{ className: 'border-[#c8ff3d]/35 bg-[#c8ff3d] !text-[#17201c]' }}>
              <span className="grid size-9 shrink-0 place-items-center rounded-sm bg-[#f7f4ea]"><KoboyoIcon src={item.icon} className="size-8" /></span>
              <span className={cn('whitespace-nowrap opacity-0 transition-opacity duration-100', railOpen && 'opacity-100')}>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      <main id="main-content" className="min-h-dvh pl-[72px]">
        <div className="mx-auto w-full max-w-[1760px] p-4 sm:p-6 lg:p-7"><Outlet /></div>
      </main>
    </div>
  )
}

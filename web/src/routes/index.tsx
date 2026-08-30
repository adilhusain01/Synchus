import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { get } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { useEffect, useRef } from 'react'

type LiveStatus = { voice_ready: boolean; voice_url: string }

export const Route = createFileRoute('/')({ component: SynchusLive })

function SynchusLive() {
  const live = useQuery({ queryKey: ['live-status'], queryFn: () => get<LiveStatus>('/api/live/status') })
  const voiceUrl = live.data?.voice_url || 'http://127.0.0.1:8765'
  const voiceFrame = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    const toggleVoice = (event: KeyboardEvent) => {
      if (event.code !== 'Space' || event.repeat) return
      event.preventDefault()
      voiceFrame.current?.contentWindow?.postMessage({ type: 'synchus-toggle-voice' }, '*')
    }
    window.addEventListener('keydown', toggleVoice)
    return () => window.removeEventListener('keydown', toggleVoice)
  }, [])

  return <main className="relative min-h-dvh overflow-hidden bg-[#050706]">
    <iframe ref={voiceFrame} title="Synchus Live voice" src={voiceUrl} className="h-dvh w-full border-0 bg-[#050706]" allow="microphone; autoplay" />
    {!live.data?.voice_ready ? <div role="status" className="absolute inset-x-4 bottom-4 mx-auto flex max-w-xl items-center justify-between gap-4 rounded-sm border border-[#39433d] bg-[#17201c]/95 p-4 text-sm text-[#f7f4ea] shadow-xl backdrop-blur">
      <span>Live voice is unavailable. Start the voice service or use written Ask.</span>
      <Button asChild variant="signal" size="sm"><Link to="/app/ask">Open Ask</Link></Button>
    </div> : null}
  </main>
}

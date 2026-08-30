import { useMemo, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import Map, { Marker } from 'react-map-gl/maplibre'
import type { StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { get, post, type AskResult } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { useUiStore } from '@/lib/store'
import { ErrorBlock, LoadingBlock, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

type RouteOptions = { origins: string[]; destinations: string[]; clients: string[] }
type Candidate = { registration: string; model: string; year: number; bs_stage: string; assessment: string; checks: string[]; note: string }
type RouteData = {
  origin: string; destination: string; client: string; travel_on: string
  path: number[][]; distance_km: number; duration_hr?: number; geometry_source: string; is_approximate: boolean
  candidates: Candidate[]
  precautions: Array<Record<string, unknown> & { rule_id: string; title: string; status: string; why_now: string; source_ref: string; lon: number; lat: number }>
  incidents: Array<Record<string, unknown> & { ticket_id: string; issue: string; severity: string; lon: number; lat: number }>
  hubs: Array<{ hub: string; lat: number; lon: number; vehicles: number; incidents: number }>
  trucks: Array<{ registration: string; model: string; year: number; bs_stage: string; home_hub: string; lat: number; lon: number }>
  uncertainty_groups: Array<{ label: string; items: string[]; effect: string }>
  origin_conflicts: Array<{ registration: string; field: string }>
}

function makeMapStyle(path: number[][]): StyleSpecification {
  return {
    version: 8,
    sources: {
      openStreetMap: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors',
      },
      route: {
        type: 'geojson',
        data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: path } },
      },
    },
    layers: [
      { id: 'open-street-map', type: 'raster', source: 'openStreetMap', minzoom: 0, maxzoom: 19 },
      { id: 'route-casing', type: 'line', source: 'route', paint: { 'line-color': '#fffaf0', 'line-width': 9, 'line-opacity': 0.95 } },
      { id: 'route-line', type: 'line', source: 'route', paint: { 'line-color': '#ff5c35', 'line-width': 5, 'line-opacity': 1 } },
    ],
  }
}

export const Route = createFileRoute('/route/')({ component: RoutePage })

function RoutePage() {
  const filters = useUiStore((state) => state.route)
  const update = useUiStore((state) => state.updateRoute)
  const [question, setQuestion] = useState('')
  const options = useQuery({ queryKey: ['route-options'], queryFn: () => get<RouteOptions>('/api/route/options') })
  const params = new URLSearchParams({ origin: filters.origin, destination: filters.destination, client: filters.client, travel_on: filters.travelOn })
  const route = useQuery({ queryKey: ['route', filters.origin, filters.destination, filters.client, filters.travelOn], queryFn: () => get<RouteData>(`/api/route?${params}`) })
  const ask = useMutation({ mutationFn: () => post<AskResult>('/api/ask', { question: `For ${filters.origin} to ${filters.destination} on ${filters.travelOn}, client ${filters.client}: ${question}` }) })
  const filteredCandidates = useMemo(() => route.data?.candidates.filter((item) => item.year >= filters.minimumYear && (filters.bsStage === 'All' || item.bs_stage === filters.bsStage)) || [], [route.data, filters.minimumYear, filters.bsStage])
  const trucks = useMemo(() => route.data?.trucks.filter((item) => item.home_hub === filters.origin && item.year >= filters.minimumYear && (filters.bsStage === 'All' || item.bs_stage === filters.bsStage)).slice(0, 36) || [], [route.data, filters])
  const routeMapStyle = useMemo(() => makeMapStyle(route.data?.path || []), [route.data?.path])
  if (options.isLoading || route.isLoading) return <LoadingBlock label="Compiling route evidence" />
  if (options.error) return <ErrorBlock error={options.error} />
  if (route.error) return <ErrorBlock error={route.error} />
  const data = route.data!
  const midpoint = data.path[Math.floor(data.path.length / 2)] || [77.2, 28.6]

  return <div className="space-y-6">
    <PageHeader icon={koboyo.route} eyebrow="Shared spatial query" title="Route intelligence" description="Fleet assignments, route evidence, map layers, and the assistant react to one selected route state." actions={<StatusPill tone={data.is_approximate ? 'warning' : 'good'}>{data.geometry_source}</StatusPill>} />
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Field label="Origin"><select name="origin" value={filters.origin} onChange={(event) => update({ origin: event.target.value, destination: event.target.value === filters.destination ? options.data!.destinations.find((item) => item !== event.target.value)! : filters.destination })}>{options.data!.origins.map((item) => <option key={item}>{item}</option>)}</select></Field>
      <Field label="Destination"><select name="destination" value={filters.destination} onChange={(event) => update({ destination: event.target.value })}>{options.data!.destinations.filter((item) => item !== filters.origin).map((item) => <option key={item}>{item}</option>)}</select></Field>
      <Field label="Client"><select name="client" value={filters.client} onChange={(event) => update({ client: event.target.value })}>{options.data!.clients.map((item) => <option key={item}>{item}</option>)}</select></Field>
      <Field label="Travel date"><input name="travel-date" type="date" autoComplete="off" value={filters.travelOn} onChange={(event) => update({ travelOn: event.target.value })} /></Field>
    </section>
    <section className="grid items-end gap-4 rounded-sm border border-[#d7d1c3] bg-white/35 p-4 md:grid-cols-[1.3fr_.7fr_auto]">
      <label><span className="mb-2 block font-['DM_Mono'] text-[10px] uppercase tracking-[.1em] text-[#66706a]">Minimum model year / {filters.minimumYear}</span><input type="range" min="2014" max="2026" value={filters.minimumYear} onChange={(event) => update({ minimumYear: Number(event.target.value) })} className="h-11 w-full accent-[#ff5c35]" /></label>
      <Field label="BS stage"><select name="bs-stage" value={filters.bsStage} onChange={(event) => update({ bsStage: event.target.value })}>{['All', 'BS6', 'BS4', 'BS3'].map((item) => <option key={item}>{item}</option>)}</select></Field>
      <label className="flex min-h-11 items-center gap-3 rounded-sm border border-[#aaa394] px-3 text-sm font-bold"><input type="checkbox" checked={filters.showHistory} onChange={(event) => update({ showHistory: event.target.checked })} className="size-4 accent-[#ff5c35]" />Historical incidents</label>
    </section>

    <div className="grid gap-5 xl:grid-cols-[.72fr_1.55fr_.73fr]">
      <Panel title={`${filteredCandidates.length} origin assignments`} eyebrow="Conditional static screening" className="max-h-[700px] overflow-y-auto">
        <div className="divide-y divide-[#d7d1c3]">{filteredCandidates.map((candidate) => <details key={candidate.registration} className="py-3 first:pt-0"><summary className="cursor-pointer list-none text-sm font-extrabold"><span className={candidate.assessment === 'STATIC BLOCK' ? 'text-[#c83a20]' : 'text-[#6a7d16]'}>{candidate.assessment}</span> / {candidate.registration} / {candidate.year} {candidate.bs_stage}</summary><p className="mt-3 text-sm">{candidate.model}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-[#59635d]">{candidate.checks.map((check) => <li key={check}>{check}</li>)}</ul></details>)}</div>
        <h3 className="mt-6 border-t-2 border-[#17201c] pt-4 font-extrabold">Route evidence</h3>{data.precautions.map((item) => <article key={item.rule_id} className="mt-3"><StatusPill tone={item.status === 'BLOCKING' ? 'critical' : 'warning'}>{item.status}</StatusPill><p className="mt-2 text-sm font-extrabold">{item.title}</p><p className="mt-1 text-xs leading-5 text-[#59635d]">{item.why_now}</p></article>)}
      </Panel>

      <section className="overflow-hidden rounded-sm border border-[#c9c2b3] bg-white">
        <Map key={`${data.origin}-${data.destination}`} initialViewState={{ longitude: midpoint[0], latitude: midpoint[1], zoom: data.distance_km < 450 ? 6.1 : 5.1, pitch: 0 }} mapStyle={routeMapStyle} attributionControl={{ compact: true }} style={{ width: '100%', height: 700 }}>
          {data.hubs.map((hub) => <Marker key={hub.hub} longitude={hub.lon} latitude={hub.lat} anchor="center"><div title={`${hub.hub}: ${hub.vehicles} home assignments`} className="grid size-10 place-items-center rounded-full border-2 border-[#17201c] bg-[#c8ff3d] font-['DM_Mono'] text-[10px] font-bold shadow-md">{hub.vehicles}</div></Marker>)}
          {trucks.map((truck, index) => <Marker key={truck.registration} longitude={truck.lon + ((index % 5) - 2) * 0.035} latitude={truck.lat + (Math.floor(index / 5) - 0.5) * 0.028} anchor="bottom"><img src={koboyo.truck} alt={`${truck.registration}: home assignment, not live location`} width={24} height={24} loading="lazy" className="h-6 w-6 object-contain drop-shadow" /></Marker>)}
          {data.precautions.map((item) => <Marker key={item.rule_id} longitude={item.lon} latitude={item.lat} anchor="bottom"><img src={koboyo.control} alt={`${item.status}: ${item.title}`} width={40} height={40} loading="lazy" className="h-10 w-10 object-contain drop-shadow" /></Marker>)}
          {filters.showHistory ? data.incidents.map((incident) => <Marker key={incident.ticket_id} longitude={incident.lon} latitude={incident.lat} anchor="center"><div title={`Historical: ${incident.issue}`} className="size-4 rounded-full border-2 border-white bg-[#2e64f5] shadow-md" /></Marker>) : null}
        </Map>
        <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-[#d7d1c3] bg-[#f7f4ea] px-4 py-3 font-['DM_Mono'] text-[9px] uppercase tracking-[.06em] text-[#626b65]"><span>Orange / route</span><span>Koboyo warning / precaution</span><span>Blue / historical</span><span>Lime / hub</span><span>Koboyo truck / home assignment</span></div>
      </section>

      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3 xl:grid-cols-1"><RouteStat label="Distance" value={`${Math.round(data.distance_km)} km`} note={data.geometry_source} /><RouteStat label="Precautions" value={String(data.precautions.length)} note="route, client, and date" /><RouteStat label="Parked now" value="Unknown" note="yard feed not connected" /></div>
        <Panel title="Route assistant"><textarea aria-label="Route question" name="route-question" autoComplete="off" value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} placeholder="e.g. What are the biggest risks, and which assigned trucks survive static checks?…" className="w-full resize-y rounded-sm border border-[#aaa394] bg-white/70 p-3 text-sm outline-none focus:border-[#2e64f5] focus:ring-3 focus:ring-[#2e64f5]/15" /><Button className="mt-3" onClick={() => ask.mutate()} disabled={!question.trim() || ask.isPending}>{ask.isPending ? 'Reasoning…' : 'Ask Route Agent'}</Button>{ask.data ? <div aria-live="polite" className="mt-4 border-l-4 border-[#2e64f5] bg-[#dfe7f4] p-4"><p className="font-extrabold">{ask.data.headline}</p><p className="mt-2 break-words text-sm leading-6 text-[#425775]">{ask.data.detail}</p></div> : null}</Panel>
        <Panel title="Why this route is conditional">{data.uncertainty_groups.map((group) => <details key={group.label} className="border-b border-[#d7d1c3] py-3 last:border-0" open><summary className="cursor-pointer text-sm font-extrabold">{group.label}</summary><ul className="mt-2 space-y-1 text-xs text-[#59635d]">{group.items.map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-2 text-xs font-bold text-[#81620e]">{group.effect}</p></details>)}</Panel>
      </div>
    </div>
  </div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block font-['DM_Mono'] text-[10px] uppercase tracking-[.1em] text-[#66706a]">{label}</span><div className="[&_input]:min-h-11 [&_input]:w-full [&_input]:rounded-sm [&_input]:border [&_input]:border-[#aaa394] [&_input]:bg-white/70 [&_input]:px-3 [&_input]:text-sm [&_input]:outline-none [&_input]:transition-[border-color,box-shadow] [&_select]:min-h-11 [&_select]:w-full [&_select]:rounded-sm [&_select]:border [&_select]:border-[#aaa394] [&_select]:bg-white/70 [&_select]:px-3 [&_select]:text-sm [&_select]:outline-none [&_select]:transition-[border-color,box-shadow] focus-within:[&_input]:border-[#2e64f5] focus-within:[&_input]:ring-3 focus-within:[&_input]:ring-[#2e64f5]/15 focus-within:[&_select]:border-[#2e64f5] focus-within:[&_select]:ring-3 focus-within:[&_select]:ring-[#2e64f5]/15">{children}</div></label>
}

function RouteStat({ label, value, note }: { label: string; value: string; note: string }) {
  return <article className="border-t-[3px] border-[#17201c] pt-3"><p className="font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#6b746e]">{label}</p><p className="mt-2 text-2xl font-extrabold tracking-[-.05em]">{value}</p><p className="mt-1 text-[11px] leading-4 text-[#68716b]">{note}</p></article>
}

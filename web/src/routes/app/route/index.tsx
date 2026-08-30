import { useEffect, useMemo, useRef, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import Map, { Marker, Popup, type MapRef } from 'react-map-gl/maplibre'
import type { Map as MapLibreMap } from 'maplibre-gl'
import type { StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { get, post, type AskResult } from '@/lib/api'
import { koboyo } from '@/lib/icons'
import { useUiStore } from '@/lib/store'
import { ErrorBlock, LoadingBlock, PageHeader, Panel, StatusPill } from '@/components/common'
import { Button } from '@/components/ui/button'

type RouteOptions = { origins: string[]; destinations: string[]; clients: string[] }
type Candidate = { registration: string; model: string; year: number; bs_stage: string; assessment: string; checks: string[]; note: string }
type MapSelection = { kind: string; title: string; longitude: number; latitude: number; rows: Array<[string, string | number]>; note?: string; offset?: [number, number] }
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

function makeMapStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      openStreetMap: {
        type: 'raster',
        tiles: [
          'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png',
          'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png',
          'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png',
        ],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors © CARTO',
      },
    },
    layers: [{ id: 'open-street-map', type: 'raster', source: 'openStreetMap', minzoom: 0, maxzoom: 19 }],
  }
}

function projectRoute(map: MapLibreMap, path: number[][]) {
  const points = path.filter((_, index) => index % 3 === 0 || index === path.length - 1).map(([lng, lat]) => map.project({ lng, lat }))
  const canvas = map.getCanvas()
  return { path: points.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' '), width: canvas.clientWidth, height: canvas.clientHeight }
}

const truckOffset = (index: number): [number, number] => [((index % 5) - 2) * 26, (Math.floor(index / 5) - 0.5) * 34 - 28]

export const Route = createFileRoute('/app/route/')({ component: RoutePage })

function RoutePage() {
  const filters = useUiStore((state) => state.route)
  const update = useUiStore((state) => state.updateRoute)
  const [question, setQuestion] = useState('')
  const [routeOverlay, setRouteOverlay] = useState({ path: '', width: 1, height: 1 })
  const [selection, setSelection] = useState<MapSelection | null>(null)
  const mapRef = useRef<MapRef>(null)
  const options = useQuery({ queryKey: ['route-options'], queryFn: () => get<RouteOptions>('/api/route/options') })
  const params = new URLSearchParams({ origin: filters.origin, destination: filters.destination, client: filters.client, travel_on: filters.travelOn })
  const route = useQuery({ queryKey: ['route', filters.origin, filters.destination, filters.client, filters.travelOn], queryFn: () => get<RouteData>(`/api/route?${params}`), placeholderData: keepPreviousData })
  const ask = useMutation({ mutationFn: () => post<AskResult>('/api/ask', { question: `For ${filters.origin} to ${filters.destination} on ${filters.travelOn}, client ${filters.client}: ${question}` }) })
  const filteredCandidates = useMemo(() => route.data?.candidates.filter((item) => item.year >= filters.minimumYear && (filters.bsStage === 'All' || item.bs_stage === filters.bsStage)) || [], [route.data, filters.minimumYear, filters.bsStage])
  const trucks = useMemo(() => route.data?.trucks.filter((item) => item.home_hub === filters.origin && item.year >= filters.minimumYear && (filters.bsStage === 'All' || item.bs_stage === filters.bsStage)).slice(0, 36) || [], [route.data, filters])
  const routeMapStyle = useMemo(() => makeMapStyle(), [])
  const routeBounds = useMemo(() => route.data?.path.reduce((bounds, point) => ({
    minLon: Math.min(bounds.minLon, point[0]), minLat: Math.min(bounds.minLat, point[1]),
    maxLon: Math.max(bounds.maxLon, point[0]), maxLat: Math.max(bounds.maxLat, point[1]),
  }), { minLon: Infinity, minLat: Infinity, maxLon: -Infinity, maxLat: -Infinity }), [route.data])

  useEffect(() => {
    const map = mapRef.current?.getMap()
    if (!map || !route.data || !routeBounds || !Number.isFinite(routeBounds.minLon)) return
    setSelection(null)
    map.fitBounds([[routeBounds.minLon, routeBounds.minLat], [routeBounds.maxLon, routeBounds.maxLat]], { padding: 96, duration: 350 })
    const frame = requestAnimationFrame(() => setRouteOverlay(projectRoute(map, route.data!.path)))
    return () => cancelAnimationFrame(frame)
  }, [route.data, routeBounds])

  if (options.isLoading || route.isLoading) return <LoadingBlock label="Compiling route evidence" />
  if (options.error) return <ErrorBlock error={options.error} />
  if (route.error && !route.data) return <ErrorBlock error={route.error} />
  const data = route.data!
  const midpoint = data.path[Math.floor(data.path.length / 2)] || [77.2, 28.6]
  const syncRouteOverlay = (map: MapLibreMap) => {
    setRouteOverlay(projectRoute(map, data.path))
  }

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

    <div className="grid items-start gap-5 xl:grid-cols-[.72fr_1.55fr_.73fr]">
      <Panel title={`${filteredCandidates.length} origin assignments`} eyebrow="Conditional static screening" className="max-h-[700px] overflow-y-auto">
        <div className="divide-y divide-[#d7d1c3]">{filteredCandidates.map((candidate) => <details key={candidate.registration} className="py-3 first:pt-0"><summary className="cursor-pointer list-none text-sm font-extrabold"><span className={candidate.assessment === 'STATIC BLOCK' ? 'text-[#c83a20]' : 'text-[#6a7d16]'}>{candidate.assessment}</span> / {candidate.registration} / {candidate.year} {candidate.bs_stage}</summary><p className="mt-3 text-sm">{candidate.model}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-[#59635d]">{candidate.checks.map((check) => <li key={check}>{check}</li>)}</ul></details>)}</div>
        <h3 className="mt-6 border-t-2 border-[#17201c] pt-4 font-extrabold">Route evidence</h3>{data.precautions.map((item) => <article key={item.rule_id} className="mt-3"><StatusPill tone={item.status === 'BLOCKING' ? 'critical' : 'warning'}>{item.status}</StatusPill><p className="mt-2 text-sm font-extrabold">{item.title}</p><p className="mt-1 text-xs leading-5 text-[#59635d]">{item.why_now}</p></article>)}
      </Panel>

      <section className="self-start overflow-hidden rounded-sm border border-[#c9c2b3] bg-white">
        <div className="relative h-[700px]">
        <Map
          ref={mapRef}
          initialViewState={{ longitude: midpoint[0], latitude: midpoint[1], zoom: data.distance_km < 450 ? 6.1 : 5.1, pitch: 0 }}
          mapStyle={routeMapStyle}
          attributionControl={{ compact: true }}
          style={{ width: '100%', height: '100%' }}
          onLoad={(event) => {
            const map = event.target
            if (routeBounds && Number.isFinite(routeBounds.minLon)) map.fitBounds([[routeBounds.minLon, routeBounds.minLat], [routeBounds.maxLon, routeBounds.maxLat]], { padding: 96, duration: 0 })
            requestAnimationFrame(() => syncRouteOverlay(map))
          }}
          onMove={(event) => syncRouteOverlay(event.target)}
          onResize={(event) => syncRouteOverlay(event.target)}
          onClick={() => setSelection(null)}
        >
          {data.hubs.map((hub) => <Marker key={hub.hub} longitude={hub.lon} latitude={hub.lat} anchor="center" onClick={(event) => { event.originalEvent.stopPropagation(); setSelection({ kind: 'Hub', title: hub.hub, longitude: hub.lon, latitude: hub.lat, rows: [['Home assignments', hub.vehicles], ['Historical incidents', hub.incidents], ['Coordinates', `${hub.lat.toFixed(3)}, ${hub.lon.toFixed(3)}`]], note: 'Assignment counts are not live parked-vehicle counts.', offset: [0, -28] }) }}><button type="button" aria-label={`Inspect ${hub.hub} hub`} title={`${hub.hub}: ${hub.vehicles} home assignments`} className="grid size-10 cursor-pointer place-items-center rounded-full border-2 border-[#17201c] bg-[#c8ff3d] font-['DM_Mono'] text-[10px] font-bold shadow-md transition-transform hover:scale-110 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#2e64f5]">{hub.vehicles}</button></Marker>)}
          {trucks.map((truck, index) => <Marker key={truck.registration} longitude={truck.lon} latitude={truck.lat} anchor="center" offset={truckOffset(index)} style={{ zIndex: '3' }} onClick={(event) => { event.originalEvent.stopPropagation(); const [x, y] = truckOffset(index); setSelection({ kind: 'Truck · home assignment', title: truck.registration, longitude: truck.lon, latitude: truck.lat, rows: [['Model', truck.model], ['Model year', truck.year], ['Emission stage', truck.bs_stage], ['Home hub', truck.home_hub]], note: 'This is its registered home assignment, not a live position.', offset: [x, y - 18] }) }}><button type="button" aria-label={`Inspect truck ${truck.registration}`} title={`${truck.registration} · ${truck.model} · home assignment`} className="cursor-pointer rounded-sm transition-transform hover:scale-125 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#2e64f5]"><img src={koboyo.truck} alt="" width={26} height={26} className="h-[26px] w-[26px] object-contain drop-shadow" /></button></Marker>)}
          {data.precautions.map((item) => <Marker key={item.rule_id} longitude={item.lon} latitude={item.lat} anchor="bottom" onClick={(event) => { event.originalEvent.stopPropagation(); setSelection({ kind: 'Route precaution', title: item.title, longitude: item.lon, latitude: item.lat, rows: [['Status', item.status], ['Rule', item.rule_id], ['Source', item.source_ref]], note: item.why_now, offset: [0, -18] }) }}><button type="button" aria-label={`Inspect precaution ${item.title}`} className="cursor-pointer rounded-sm transition-transform hover:scale-110 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#2e64f5]"><img src={koboyo.control} alt="" width={40} height={40} loading="lazy" className="h-10 w-10 object-contain drop-shadow" /></button></Marker>)}
          {filters.showHistory ? data.incidents.map((incident) => <Marker key={incident.ticket_id} longitude={incident.lon} latitude={incident.lat} anchor="center" onClick={(event) => { event.originalEvent.stopPropagation(); setSelection({ kind: 'Historical incident', title: incident.issue, longitude: incident.lon, latitude: incident.lat, rows: [['Ticket', incident.ticket_id], ['Severity', incident.severity], ['Evidence state', 'Historical']], note: 'Useful for patterns and precedent; not a current road condition.', offset: [0, -16] }) }}><button type="button" aria-label={`Inspect historical incident ${incident.issue}`} title={`Historical: ${incident.issue}`} className="block size-4 cursor-pointer rounded-full border-2 border-white bg-[#2e64f5] shadow-md transition-transform hover:scale-125 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#17201c]" /></Marker>) : null}
          {selection ? <Popup longitude={selection.longitude} latitude={selection.latitude} anchor="bottom" offset={selection.offset || 24} closeOnClick={false} onClose={() => setSelection(null)} maxWidth="320px" className="z-30 [&_.maplibregl-popup-close-button]:right-2 [&_.maplibregl-popup-close-button]:top-2 [&_.maplibregl-popup-close-button]:z-10 [&_.maplibregl-popup-close-button]:grid [&_.maplibregl-popup-close-button]:size-8 [&_.maplibregl-popup-close-button]:place-items-center [&_.maplibregl-popup-close-button]:rounded-full [&_.maplibregl-popup-close-button]:bg-white/65 [&_.maplibregl-popup-close-button]:text-lg [&_.maplibregl-popup-close-button]:text-[#48534d] [&_.maplibregl-popup-close-button]:transition-colors hover:[&_.maplibregl-popup-close-button]:bg-white [&_.maplibregl-popup-content]:!rounded-2xl [&_.maplibregl-popup-content]:!bg-[#fffaf0] [&_.maplibregl-popup-content]:!p-0 [&_.maplibregl-popup-content]:shadow-[0_18px_50px_rgba(31,46,38,.2)] [&_.maplibregl-popup-tip]:!border-t-[#fffaf0]"><MapInspector selection={selection} /></Popup> : null}
        </Map>
        {routeOverlay.path ? <svg aria-label={`${data.origin} to ${data.destination} road route`} role="img" viewBox={`0 0 ${routeOverlay.width} ${routeOverlay.height}`} preserveAspectRatio="none" className="pointer-events-none absolute inset-0 z-[2] size-full overflow-visible">
          <path d={routeOverlay.path} fill="none" stroke="#fffaf0" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
          <path d={routeOverlay.path} fill="none" stroke="#ff5c35" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        </svg> : null}
        {route.isFetching ? <div role="status" aria-live="polite" className="pointer-events-none absolute right-3 top-3 z-20 flex items-center gap-2 rounded-full border border-[#aaa394] bg-[#fffaf0]/95 px-3 py-2 font-['DM_Mono'] text-[9px] uppercase tracking-[.08em] text-[#4d5651] shadow-md backdrop-blur"><span className="size-3.5 animate-spin rounded-full border-2 border-[#a6afa9] border-t-[#17201c]" aria-hidden="true" />Updating route</div> : null}
        {route.isError && route.data ? <div role="status" className="pointer-events-none absolute right-3 top-3 z-20 rounded-full border border-[#d8a013]/50 bg-[#fff4bf]/95 px-3 py-2 font-['DM_Mono'] text-[9px] uppercase tracking-[.08em] text-[#72550c] shadow-md backdrop-blur">Update failed · showing previous route</div> : null}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-[#d7d1c3] bg-[#f7f4ea] px-4 py-3 font-['DM_Mono'] text-[9px] uppercase tracking-[.06em] text-[#626b65]"><span>Orange / route</span><span>Koboyo warning / precaution</span><span>Blue / historical</span><span>Lime / hub</span><span>{trucks.length} Koboyo trucks / filtered home assignments</span></div>
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

function MapInspector({ selection }: { selection: MapSelection }) {
  return <article className="min-w-[260px] overflow-hidden rounded-2xl bg-[#fffaf0] text-[#17201c]"><header className="border-b border-[#d8d1c3] bg-[#e8f0df] px-4 py-3.5 pr-12"><p className="font-['DM_Mono'] text-[9px] uppercase tracking-[.1em] text-[#61751a]">{selection.kind}</p><h3 className="mt-1.5 text-lg font-extrabold tracking-[-.035em]">{selection.title}</h3></header><dl className="divide-y divide-[#e1dbce] px-4">{selection.rows.map(([label, value]) => <div key={label} className="grid grid-cols-[1fr_auto] gap-4 py-3 text-xs"><dt className="text-[#6b756f]">{label}</dt><dd className="max-w-40 text-right font-extrabold text-[#26312b]">{value}</dd></div>)}</dl>{selection.note ? <p className="border-t border-[#d8d1c3] bg-[#fff4bf]/65 px-4 py-3 text-[11px] leading-4 text-[#66551c]">{selection.note}</p> : null}</article>
}

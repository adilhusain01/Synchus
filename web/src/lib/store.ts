import { create } from 'zustand'

type RouteFilters = {
  origin: string; destination: string; client: string; travelOn: string
  minimumYear: number; bsStage: string; showHistory: boolean
}

type UiStore = {
  compactRail: boolean
  setCompactRail: (value: boolean) => void
  route: RouteFilters
  updateRoute: (patch: Partial<RouteFilters>) => void
}

export const useUiStore = create<UiStore>((set) => ({
  compactRail: false,
  setCompactRail: (compactRail) => set({ compactRail }),
  route: {
    origin: 'Delhi', destination: 'Ludhiana', client: 'Internal', travelOn: '2026-08-30',
    minimumYear: 2014, bsStage: 'All', showHistory: true,
  },
  updateRoute: (patch) => set((state) => ({ route: { ...state.route, ...patch } })),
}))

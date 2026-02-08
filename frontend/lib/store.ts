import { create } from 'zustand'
import { Episode, VerifiedFact } from './api'

interface AppState {
  // User state
  apiKey: string | null
  setApiKey: (key: string) => void
  clearApiKey: () => void

  // Query state
  currentQuery: string
  setCurrentQuery: (query: string) => void

  // Results cache
  episodesCache: Map<string, Episode>
  cacheEpisode: (id: string, episode: Episode) => void
  getEpisode: (id: string) => Episode | undefined

  factsCache: Map<string, VerifiedFact[]>
  cacheFacts: (queryId: string, facts: VerifiedFact[]) => void
  getFacts: (queryId: string) => VerifiedFact[] | undefined

  // UI state
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Theme state (managed by next-themes)
  theme: 'light' | 'dark' | 'system'
  setTheme: (theme: 'light' | 'dark' | 'system') => void
}

export const useStore = create<AppState>((set, get) => ({
  // User state
  apiKey: null,
  setApiKey: (key) => {
    set({ apiKey: key })
    if (typeof window !== 'undefined') {
      localStorage.setItem('api_key', key)
    }
  },
  clearApiKey: () => {
    set({ apiKey: null })
    if (typeof window !== 'undefined') {
      localStorage.removeItem('api_key')
    }
  },

  // Query state
  currentQuery: '',
  setCurrentQuery: (query) => set({ currentQuery: query }),

  // Results cache
  episodesCache: new Map(),
  cacheEpisode: (id, episode) =>
    set((state) => ({
      episodesCache: new Map(state.episodesCache).set(id, episode),
    })),
  getEpisode: (id) => get().episodesCache.get(id),

  factsCache: new Map(),
  cacheFacts: (queryId, facts) =>
    set((state) => ({
      factsCache: new Map(state.factsCache).set(queryId, facts),
    })),
  getFacts: (queryId) => get().factsCache.get(queryId),

  // UI state
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // Theme state
  theme: 'dark',
  setTheme: (theme) => set({ theme }),
}))

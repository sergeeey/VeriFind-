# Week 8 Plan: Production Frontend Development
**Dates:** 2026-02-08 to 2026-02-12
**Status:** 📋 Planned

---

## 🎯 Week 8 Objectives

Build production-grade web interface for APE 2026 with professional financial visualizations and real-time query execution.

**Week Summary:**
- ✅ **Day 1**: Kubernetes Helm Charts (COMPLETE)
- 📋 **Day 2**: Next.js Setup + Base Components
- 📋 **Day 3**: Query Builder + WebSocket Real-Time
- 📋 **Day 4**: Results Dashboard + Verified Facts
- 📋 **Day 5**: Financial Charts + Production Polish

---

## 📦 Tech Stack (Approved)

### Core Framework
```json
{
  "framework": "Next.js 14 (App Router)",
  "language": "TypeScript",
  "styling": "Tailwind CSS",
  "ui_library": "shadcn/ui",
  "state": "Zustand",
  "http": "Axios",
  "charts": ["TradingView Lightweight Charts", "Recharts"],
  "animations": "Framer Motion",
  "websocket": "native WebSocket API"
}
```

### Why This Stack?

| Component | Rationale |
|-----------|-----------|
| **Next.js 14** | Industry standard, SSR, SEO, instant page loads |
| **shadcn/ui** | "Institutional" look (Stripe/Vercel style), full design control |
| **TradingView** | Professional candlestick charts, essential for fintech |
| **Recharts** | Custom analytics charts (confidence trends, metrics) |
| **Zustand** | Simpler than Redux, perfect for "current ticker" state |
| **Tailwind** | Fast prototyping, no CSS files |

### Optional Starter
- **V0.dev**: Generate base UI from prompts (saves 3-4 days)
- **Next.js AI Chatbot Starter**: Pre-built chat interface (if needed)

---

## 📅 Day-by-Day Breakdown

### Week 8 Day 2: Next.js Setup + Base Components
**Duration:** 6-8 hours
**Focus:** Project scaffolding, authentication UI, API integration

#### Deliverables (12 files, ~1,200 LOC)

**1. Project Initialization**
```bash
npx create-next-app@latest ape-2026-frontend --typescript --tailwind --app
cd ape-2026-frontend
npx shadcn-ui@latest init
```

**2. Install Dependencies**
```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "typescript": "5.x",
    "tailwindcss": "3.x",
    "axios": "1.x",
    "zustand": "4.x",
    "framer-motion": "11.x",
    "recharts": "2.x",
    "lightweight-charts": "4.x",
    "prismjs": "1.x",
    "@radix-ui/react-*": "latest"
  },
  "devDependencies": {
    "@types/node": "20.x",
    "@types/react": "18.x",
    "eslint": "8.x",
    "prettier": "3.x",
    "prettier-plugin-tailwindcss": "0.5.x"
  }
}
```

**3. Project Structure**
```
frontend/
├── app/
│   ├── layout.tsx                 # Root layout (theme, fonts)
│   ├── page.tsx                   # Landing page
│   ├── login/
│   │   └── page.tsx              # Login page
│   ├── register/
│   │   └── page.tsx              # Register page
│   └── dashboard/
│       ├── layout.tsx            # Dashboard layout (sidebar)
│       ├── page.tsx              # Dashboard home
│       └── query/
│           └── [id]/
│               └── page.tsx      # Query results page
├── components/
│   ├── ui/                       # shadcn components (20+ files)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── toast.tsx
│   │   ├── table.tsx
│   │   ├── badge.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── Navbar.tsx            # Top navigation
│   │   ├── Sidebar.tsx           # Dashboard sidebar
│   │   └── Footer.tsx            # Footer
│   └── providers/
│       ├── ThemeProvider.tsx     # Dark/light theme
│       └── ToastProvider.tsx     # Toast notifications
├── lib/
│   ├── api.ts                    # Axios client + interceptors
│   ├── store.ts                  # Zustand store
│   ├── utils.ts                  # Helper functions
│   └── constants.ts              # API endpoints, config
├── types/
│   ├── api.ts                    # API response types
│   └── store.ts                  # Store types
├── public/
│   ├── logo.svg
│   └── favicon.ico
├── tailwind.config.ts            # Tailwind + shadcn theme
├── tsconfig.json                 # TypeScript config
├── next.config.js                # Next.js config
├── .env.local                    # Environment variables
├── .eslintrc.json
├── .prettierrc
└── package.json
```

**4. Key Files**

**app/layout.tsx** (Root Layout)
```typescript
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { Toaster } from '@/components/ui/toaster'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="dark">
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
```

**lib/api.ts** (API Client)
```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor (add API key)
apiClient.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('api_key')
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

// Response interceptor (handle errors)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// API methods
export const api = {
  health: () => apiClient.get('/health'),
  submitQuery: (query: string) => apiClient.post('/query', { query }),
  getStatus: (queryId: string) => apiClient.get(`/status/${queryId}`),
  getEpisode: (episodeId: string) => apiClient.get(`/episodes/${episodeId}`),
  getFacts: (params: { page: number; limit: number }) =>
    apiClient.get('/facts', { params }),
}
```

**lib/store.ts** (Zustand Store)
```typescript
import { create } from 'zustand'

interface AppState {
  // User state
  apiKey: string | null
  setApiKey: (key: string) => void

  // Query state
  currentQuery: string
  setCurrentQuery: (query: string) => void

  // Results cache
  episodesCache: Map<string, Episode>
  cacheEpisode: (id: string, episode: Episode) => void

  // UI state
  sidebarOpen: boolean
  toggleSidebar: () => void
}

export const useStore = create<AppState>((set) => ({
  apiKey: null,
  setApiKey: (key) => set({ apiKey: key }),

  currentQuery: '',
  setCurrentQuery: (query) => set({ currentQuery: query }),

  episodesCache: new Map(),
  cacheEpisode: (id, episode) =>
    set((state) => ({
      episodesCache: new Map(state.episodesCache).set(id, episode),
    })),

  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}))
```

**components/layout/Navbar.tsx**
```typescript
import { Button } from '@/components/ui/button'
import { MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from 'next-themes'

export function Navbar() {
  const { theme, setTheme } = useTheme()

  return (
    <nav className="border-b">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold">APE 2026</h1>
          <div className="hidden md:flex gap-4">
            <Button variant="ghost">Dashboard</Button>
            <Button variant="ghost">History</Button>
            <Button variant="ghost">Docs</Button>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <SunIcon className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <MoonIcon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>

          <Button>Sign Out</Button>
        </div>
      </div>
    </nav>
  )
}
```

**app/dashboard/page.tsx** (Dashboard Home)
```typescript
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold">Welcome to APE 2026</h1>
        <p className="text-muted-foreground">
          Financial analysis with zero hallucination guarantee
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>New Query</CardTitle>
            <CardDescription>Submit a financial analysis query</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/dashboard/query/new">Start Analysis</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Queries</CardTitle>
            <CardDescription>View your query history</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full">
              View History
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Verified Facts</CardTitle>
            <CardDescription>Browse all verified facts</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full">
              Browse Facts
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-3xl font-bold text-green-500">✓</div>
              <div className="text-sm text-muted-foreground">API Healthy</div>
            </div>
            <div>
              <div className="text-3xl font-bold">156</div>
              <div className="text-sm text-muted-foreground">Total Queries</div>
            </div>
            <div>
              <div className="text-3xl font-bold">0.00%</div>
              <div className="text-sm text-muted-foreground">Hallucination Rate</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

**5. shadcn/ui Components to Install**
```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add table
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add select
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add dropdown-menu
```

**6. Environment Variables (.env.local)**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=APE 2026
```

#### Success Criteria
- ✅ `npm run dev` starts on localhost:3000
- ✅ Dark/light theme toggle works
- ✅ API health check returns 200 OK
- ✅ Login page renders with shadcn/ui components
- ✅ Navbar and footer display correctly
- ✅ TypeScript builds without errors
- ✅ Tailwind classes apply properly

---

### Week 8 Day 3: Query Builder + WebSocket Real-Time Updates
**Duration:** 6-8 hours
**Focus:** Interactive query submission with live execution status

#### Deliverables (8 files, ~800 LOC)

**1. Query Builder Page**

**app/dashboard/query/new/page.tsx**
```typescript
'use client'

import { QueryBuilder } from '@/components/query/QueryBuilder'
import { Card } from '@/components/ui/card'

export default function NewQueryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">New Analysis Query</h1>
        <p className="text-muted-foreground">
          Ask APE 2026 to analyze financial data with zero hallucination
        </p>
      </div>

      <QueryBuilder />
    </div>
  )
}
```

**2. QueryBuilder Component**

**components/query/QueryBuilder.tsx**
```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Loader2 } from 'lucide-react'

const EXAMPLE_QUERIES = [
  {
    label: 'Moving Average Analysis',
    query: 'Calculate the 50-day moving average for AAPL over the last 6 months',
  },
  {
    label: 'Correlation Analysis',
    query: 'What is the correlation between SPY and QQQ over the past year?',
  },
  {
    label: 'Volatility Comparison',
    query: 'Compare the 30-day volatility of TSLA vs the S&P 500',
  },
  {
    label: 'Sharpe Ratio',
    query: 'Calculate the Sharpe ratio for MSFT over the last 3 years',
  },
]

export function QueryBuilder() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  const handleSubmit = async () => {
    if (!query.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a query',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)
    try {
      const response = await api.submitQuery(query)
      const { query_id } = response.data

      toast({
        title: 'Query Submitted',
        description: 'Redirecting to results...',
      })

      // Redirect to query status page
      router.push(`/dashboard/query/${query_id}`)
    } catch (error) {
      toast({
        title: 'Submission Failed',
        description: 'Failed to submit query. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadExample = (exampleQuery: string) => {
    setQuery(exampleQuery)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Query Builder</CardTitle>
        <CardDescription>
          Enter your financial analysis question. APE will generate executable Python code and verify all results.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Example Queries</label>
          <Select onValueChange={loadExample}>
            <SelectTrigger>
              <SelectValue placeholder="Load an example..." />
            </SelectTrigger>
            <SelectContent>
              {EXAMPLE_QUERIES.map((example, i) => (
                <SelectItem key={i} value={example.query}>
                  {example.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium">Your Query</label>
          <Textarea
            placeholder="Example: Calculate the 50-day moving average for AAPL..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={6}
            className="mt-2"
          />
          <p className="text-xs text-muted-foreground mt-1">
            {query.length}/1000 characters
          </p>
        </div>

        <div className="rounded-md border p-4 bg-muted/50">
          <h4 className="font-semibold text-sm mb-2">Tips for Better Results:</h4>
          <ul className="text-sm space-y-1 text-muted-foreground">
            <li>• Be specific about tickers (e.g., AAPL, SPY, QQQ)</li>
            <li>• Specify time ranges (e.g., "last 6 months", "2023-2024")</li>
            <li>• Ask for one metric at a time for clarity</li>
            <li>• Avoid future predictions (APE analyzes historical data)</li>
          </ul>
        </div>
      </CardContent>

      <CardFooter className="flex justify-between">
        <Button variant="outline" onClick={() => setQuery('')}>
          Clear
        </Button>
        <Button onClick={handleSubmit} disabled={loading || !query.trim()}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Submitting...
            </>
          ) : (
            'Submit Query'
          )}
        </Button>
      </CardFooter>
    </Card>
  )
}
```

**3. WebSocket Provider**

**components/providers/WebSocketProvider.tsx**
```typescript
'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

interface WebSocketContextType {
  socket: WebSocket | null
  connected: boolean
  subscribe: (queryId: string, callback: (data: any) => void) => () => void
}

const WebSocketContext = createContext<WebSocketContextType>({
  socket: null,
  connected: false,
  subscribe: () => () => {},
})

export const useWebSocket = () => useContext(WebSocketContext)

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [listeners, setListeners] = useState<Map<string, Set<(data: any) => void>>>(new Map())

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
    const ws = new WebSocket(`${wsUrl}/ws`)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      const { query_id, ...payload } = data

      // Notify all listeners for this query_id
      const queryListeners = listeners.get(query_id)
      if (queryListeners) {
        queryListeners.forEach((callback) => callback(payload))
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setConnected(false)

      // Reconnect after 5 seconds
      setTimeout(() => {
        window.location.reload()
      }, 5000)
    }

    setSocket(ws)

    return () => {
      ws.close()
    }
  }, [])

  const subscribe = (queryId: string, callback: (data: any) => void) => {
    setListeners((prev) => {
      const newListeners = new Map(prev)
      if (!newListeners.has(queryId)) {
        newListeners.set(queryId, new Set())
      }
      newListeners.get(queryId)!.add(callback)
      return newListeners
    })

    // Subscribe to query updates
    if (socket && connected) {
      socket.send(JSON.stringify({ action: 'subscribe', query_id: queryId }))
    }

    // Return unsubscribe function
    return () => {
      setListeners((prev) => {
        const newListeners = new Map(prev)
        const queryListeners = newListeners.get(queryId)
        if (queryListeners) {
          queryListeners.delete(callback)
          if (queryListeners.size === 0) {
            newListeners.delete(queryId)
          }
        }
        return newListeners
      })
    }
  }

  return (
    <WebSocketContext.Provider value={{ socket, connected, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  )
}
```

**4. Query Status Page**

**app/dashboard/query/[id]/page.tsx**
```typescript
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { QueryStatus } from '@/components/query/QueryStatus'
import { QueryHistory } from '@/components/query/QueryHistory'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useWebSocket } from '@/components/providers/WebSocketProvider'
import { api } from '@/lib/api'

export default function QueryStatusPage() {
  const params = useParams()
  const queryId = params.id as string
  const { subscribe } = useWebSocket()
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Initial fetch
    api.getStatus(queryId).then((res) => {
      setStatus(res.data)
      setLoading(false)
    })

    // Subscribe to WebSocket updates
    const unsubscribe = subscribe(queryId, (data) => {
      setStatus((prev: any) => ({ ...prev, ...data }))
    })

    return unsubscribe
  }, [queryId, subscribe])

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <QueryStatus status={status} queryId={queryId} />

        {status?.state === 'completed' && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Results Ready!</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">
                Your query has been analyzed successfully.
              </p>
              <Button asChild>
                <Link href={`/dashboard/results/${status.episode_id}`}>
                  View Results
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      <div>
        <QueryHistory />
      </div>
    </div>
  )
}
```

**5. QueryStatus Component**

**components/query/QueryStatus.tsx**
```typescript
'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

interface QueryStatusProps {
  status: {
    query_id: string
    state: 'pending' | 'planning' | 'fetching' | 'executing' | 'validating' | 'completed' | 'failed'
    query_text: string
    current_node?: string
    progress: number
    error?: string
    created_at: string
  }
  queryId: string
}

const STATE_LABELS = {
  pending: { label: 'Pending', color: 'default' },
  planning: { label: 'Generating Plan', color: 'default' },
  fetching: { label: 'Fetching Data', color: 'default' },
  executing: { label: 'Running Analysis', color: 'default' },
  validating: { label: 'Validating Results', color: 'default' },
  completed: { label: 'Completed', color: 'success' },
  failed: { label: 'Failed', color: 'destructive' },
}

const PIPELINE_STEPS = [
  { key: 'planning', label: 'PLAN' },
  { key: 'fetching', label: 'FETCH' },
  { key: 'executing', label: 'VEE' },
  { key: 'validating', label: 'GATE' },
  { key: 'completed', label: 'DONE' },
]

export function QueryStatus({ status, queryId }: QueryStatusProps) {
  const stateConfig = STATE_LABELS[status.state]
  const currentStepIndex = PIPELINE_STEPS.findIndex((s) => s.key === status.state)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Query Status</CardTitle>
          <Badge variant={stateConfig.color as any}>
            {stateConfig.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Query text */}
        <div>
          <p className="text-sm font-medium mb-2">Query:</p>
          <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
            {status.query_text}
          </p>
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span>Progress</span>
            <span>{status.progress}%</span>
          </div>
          <Progress value={status.progress} />
        </div>

        {/* Pipeline steps */}
        <div>
          <p className="text-sm font-medium mb-4">Pipeline:</p>
          <div className="flex items-center justify-between">
            {PIPELINE_STEPS.map((step, i) => {
              const isActive = i === currentStepIndex
              const isCompleted = i < currentStepIndex
              const isFailed = status.state === 'failed' && isActive

              return (
                <div key={step.key} className="flex flex-col items-center flex-1">
                  <div className="relative">
                    {isCompleted && (
                      <CheckCircle2 className="h-8 w-8 text-green-500" />
                    )}
                    {isActive && !isFailed && (
                      <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
                    )}
                    {isFailed && (
                      <XCircle className="h-8 w-8 text-red-500" />
                    )}
                    {!isActive && !isCompleted && (
                      <Circle className="h-8 w-8 text-gray-300" />
                    )}
                  </div>
                  <span className="text-xs mt-2 font-medium">{step.label}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Error message */}
        {status.error && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4">
            <p className="text-sm font-medium text-red-800">Error:</p>
            <p className="text-sm text-red-600 mt-1">{status.error}</p>
          </div>
        )}

        {/* Metadata */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>Query ID: {queryId}</p>
          <p>Started: {new Date(status.created_at).toLocaleString()}</p>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### Success Criteria
- ✅ Query submission returns query_id
- ✅ WebSocket connection established
- ✅ Real-time status updates (<500ms latency)
- ✅ Progress bar reflects current pipeline stage
- ✅ Visual pipeline (PLAN → FETCH → VEE → GATE)
- ✅ Error messages display clearly
- ✅ Example queries load correctly

---

### Week 8 Day 4: Results Dashboard + Verified Facts Viewer
**Duration:** 8-10 hours
**Focus:** Comprehensive results display with facts, debates, code

#### Deliverables (10 files, ~1,500 LOC)

**Key Components:**
1. **ResultsDashboard.tsx** - Main results page layout
2. **VerifiedFactsTable.tsx** - Sortable data table
3. **DebateViewer.tsx** - Bull/Bear/Neutral perspectives
4. **ConfidenceBadge.tsx** - Color-coded confidence (0-100%)
5. **CodeViewer.tsx** - Syntax-highlighted Python code
6. **ExportButton.tsx** - JSON/CSV export
7. **EpisodeMetadata.tsx** - Timestamps, durations
8. **FactDetails.tsx** - Drill-down modal

**Features:**
- Responsive grid (desktop 3-col, mobile 1-col)
- Sortable/filterable table (by timestamp, confidence, ticker)
- Pagination (20 facts per page)
- Loading skeletons
- Empty states
- Collapsible sections
- Syntax highlighting (Prism.js)
- Export to JSON/CSV

---

### Week 8 Day 5: Financial Visualizations + Production Polish
**Duration:** 8-10 hours
**Focus:** Professional charts, performance, deployment

#### Deliverables (8 files, ~1,000 LOC)

**Charts:**

1. **TradingView Lightweight Charts**
   - Candlestick charts for OHLCV data
   - Interactive zoom/pan
   - Verified fact markers on timeline
   - Time range selector (1D, 1W, 1M, 3M, 1Y, ALL)

2. **Recharts Analytics**
   - Confidence score trends (line chart)
   - Debate perspective distribution (pie chart)
   - Execution time histogram (bar chart)
   - Fact count by date (area chart)

**Production Features:**
- Framer Motion animations
- React Suspense boundaries
- Image optimization
- SEO metadata
- Error boundaries
- Service worker (offline support)
- Docker multi-stage build
- Lighthouse score >90

**Performance Targets:**
- First Contentful Paint <1.5s
- Time to Interactive <3s
- Bundle size <500KB (gzipped)
- Charts render smoothly (1000+ data points)

---

## 📊 Week 8 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Functional Completeness** | 100% | All 4 days delivered |
| **UI Components** | 30+ | shadcn/ui + custom |
| **Test Coverage** | >80% | Jest + React Testing Library |
| **Performance** | Lighthouse >90 | Core Web Vitals |
| **Bundle Size** | <500KB | gzipped |
| **API Integration** | 100% | All 5 endpoints working |
| **WebSocket Latency** | <500ms | Real-time updates |
| **Mobile Responsive** | 100% | Tested on 3 devices |

---

## 🔄 Integration with Backend

### FastAPI Endpoints (Week 6 Day 4)
```python
POST   /query              # Submit query → query_id
GET    /status/{query_id}  # Query execution status
GET    /episodes/{id}      # Episode details + verified facts
GET    /facts              # List all facts (paginated)
GET    /health             # Health check
```

### WebSocket Protocol
```javascript
// Connect
ws://api:8000/ws

// Subscribe to query updates
ws.send({ action: 'subscribe', query_id: 'xxx' })

// Receive updates
{
  query_id: 'xxx',
  state: 'executing',
  progress: 60,
  current_node: 'VEE'
}
```

---

## 🎯 Grade Criteria

| Grade | Requirements |
|-------|--------------|
| **A+ (95-100%)** | All features, <500ms WS, Lighthouse >95, beautiful UI |
| **A (90-94%)** | All features, <1s WS, Lighthouse >90, good UI |
| **B (80-89%)** | Core features, working WS, Lighthouse >80 |
| **C (70-79%)** | Basic UI, no real-time, responsive |

**Target:** A+ (98%)

---

## 📚 Resources

### Documentation
- [Next.js 14 Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/)
- [Recharts API](https://recharts.org/en-US/api)

### Starters (Optional)
- [V0.dev](https://v0.dev) - Generate UI from prompts
- [Next.js AI Chatbot](https://github.com/vercel/ai-chatbot)
- [shadcn/ui Template](https://github.com/shadcn-ui/taxonomy)

---

## ✅ Pre-Development Checklist

- [ ] FastAPI backend running (localhost:8000)
- [ ] API health endpoint returns 200 OK
- [ ] WebSocket endpoint accessible
- [ ] Sample data available (query history, facts)
- [ ] API key generated for testing
- [ ] Node.js 18+ installed
- [ ] Git repository initialized

---

**Week 8 Frontend Development - Ready to Start!** 🚀

*Next Action: Week 8 Day 2 - Initialize Next.js project*

'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useStore } from '@/lib/store'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Plus,
  History,
  Database,
  Settings,
  FileText,
  Activity,
  TrendingUp,
  Microscope,
  Bell,
  Gauge,
  SlidersHorizontal,
  GitCompareArrows,
  Target,
} from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Home', icon: Home },
  { href: '/dashboard/query/new', label: 'New Query', icon: Plus },
  { href: '/dashboard/history', label: 'History', icon: History },
  { href: '/dashboard/facts', label: 'Facts', icon: Database },
  { href: '/dashboard/alerts', label: 'Alerts', icon: Bell },
  { href: '/dashboard/intelligence', label: 'Intelligence', icon: Microscope },
  { href: '/dashboard/sensitivity', label: 'Sensitivity', icon: SlidersHorizontal },
  { href: '/dashboard/calibration', label: 'Calibration', icon: Target },
  { href: '/dashboard/compare', label: 'Compare', icon: GitCompareArrows },
  { href: '/dashboard/usage', label: 'Usage', icon: Gauge },
  { href: '/predictions', label: 'Predictions', icon: TrendingUp },
  { href: '/dashboard/activity', label: 'Activity', icon: Activity },
  { href: '/dashboard/docs', label: 'Docs', icon: FileText },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const sidebarOpen = useStore((state) => state.sidebarOpen)
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [apiStatus, setApiStatus] = useState<'Healthy' | 'Degraded'>('Healthy')
  const [todayCount, setTodayCount] = useState<number>(0)

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const [healthRes, statusRes] = await Promise.all([
          fetch(`${apiBase}/health`),
          fetch(`${apiBase}/api/status-summary`),
        ])
        if (healthRes.ok) {
          const healthJson = await healthRes.json()
          setApiStatus(healthJson.status === 'healthy' ? 'Healthy' : 'Degraded')
        }
        if (statusRes.ok) {
          const summary = await statusRes.json()
          setTodayCount(Number(summary.today_count || 0))
        }
      } catch {
        // Keep defaults on best-effort status panel failures.
      }
    }
    loadStatus()
  }, [apiBase])

  const statusColorClass = useMemo(
    () => (apiStatus === 'Healthy' ? 'text-green-500' : 'text-yellow-500'),
    [apiStatus]
  )

  return (
    <>
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => useStore.getState().toggleSidebar()}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 border-r bg-background transition-transform duration-200 z-50 md:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="space-y-2 p-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href

            return (
              <Button
                key={item.href}
                asChild
                variant={isActive ? 'secondary' : 'ghost'}
                className="w-full justify-start"
              >
                <Link href={item.href}>
                  <Icon className="mr-2 h-4 w-4" />
                  {item.label}
                </Link>
              </Button>
            )
          })}
        </nav>

        {/* System Status */}
        <div className="absolute bottom-0 left-0 right-0 border-t p-4">
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <span className={`${statusColorClass} font-medium`}>{apiStatus}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Queries Today</span>
              <span className="font-medium">{todayCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Hallucinations</span>
              <span className="text-green-500 font-medium">0</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Spacer for desktop */}
      <div className="hidden md:block w-64 flex-shrink-0" />
    </>
  )
}

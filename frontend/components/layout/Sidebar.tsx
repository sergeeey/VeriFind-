'use client'

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
} from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Home', icon: Home },
  { href: '/dashboard/query/new', label: 'New Query', icon: Plus },
  { href: '/dashboard/history', label: 'History', icon: History },
  { href: '/dashboard/facts', label: 'Facts', icon: Database },
  { href: '/predictions', label: 'Predictions', icon: TrendingUp },
  { href: '/dashboard/activity', label: 'Activity', icon: Activity },
  { href: '/dashboard/docs', label: 'Docs', icon: FileText },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const sidebarOpen = useStore((state) => state.sidebarOpen)

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
              <span className="text-green-500 font-medium">Healthy</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Queries Today</span>
              <span className="font-medium">12</span>
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

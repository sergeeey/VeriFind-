'use client'

import { Button } from '@/components/ui/button'
import { BarChart3, Moon, Sun, LogOut, Menu } from 'lucide-react'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { useToast } from '@/components/ui/use-toast'

export function Navbar() {
  const { theme, setTheme } = useTheme()
  const router = useRouter()
  const { toast } = useToast()
  const clearApiKey = useStore((state) => state.clearApiKey)
  const toggleSidebar = useStore((state) => state.toggleSidebar)

  const handleLogout = () => {
    clearApiKey()
    toast({
      title: 'Logged Out',
      description: 'You have been logged out successfully',
    })
    router.push('/login')
  }

  return (
    <nav className="border-b">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={toggleSidebar}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <Link href="/dashboard" className="flex items-center gap-2">
            <BarChart3 className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold">APE 2026</h1>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>

          <Button variant="ghost" size="icon" onClick={handleLogout}>
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </nav>
  )
}

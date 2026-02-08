'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/layout/Navbar'
import { Sidebar } from '@/components/layout/Sidebar'
import DisclaimerBanner from '@/components/layout/DisclaimerBanner'
import { useStore } from '@/lib/store'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const apiKey = useStore((state) => state.apiKey)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted) {
      const storedKey = localStorage.getItem('api_key')
      if (!storedKey && !apiKey) {
        router.push('/login')
      } else if (storedKey && !apiKey) {
        useStore.getState().setApiKey(storedKey)
      }
    }
  }, [mounted, apiKey, router])

  if (!mounted) {
    return null
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <div className="container max-w-7xl">
            {/* Legal Disclaimer Banner - Week 11 Day 3 */}
            <DisclaimerBanner dismissible={true} />

            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

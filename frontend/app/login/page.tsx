'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import { useStore } from '@/lib/store'
import Link from 'next/link'
import { BarChart3 } from 'lucide-react'

export default function LoginPage() {
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { toast } = useToast()
  const setStoreApiKey = useStore((state) => state.setApiKey)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!apiKey.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter your API key',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      // Validate API key with health check
      const response = await fetch('/api/health', {
        headers: {
          'X-API-Key': apiKey,
        },
      })

      if (response.ok) {
        // Store API key
        localStorage.setItem('api_key', apiKey)
        setStoreApiKey(apiKey)

        toast({
          title: 'Success',
          description: 'Login successful!',
        })

        // Redirect to dashboard
        router.push('/dashboard')
      } else {
        throw new Error('Invalid API key')
      }
    } catch (error) {
      toast({
        title: 'Login Failed',
        description: 'Invalid API key. Please check and try again.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <BarChart3 className="h-10 w-10 text-primary" />
          <h1 className="text-3xl font-bold">APE 2026</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Login</CardTitle>
            <CardDescription>
              Enter your API key to access the dashboard
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleLogin}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="apiKey">API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="sk-ape-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Don't have an API key?{' '}
                  <Link href="/register" className="text-primary hover:underline">
                    Register here
                  </Link>
                </p>
              </div>
            </CardContent>

            <CardFooter>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Logging in...' : 'Login'}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <div className="mt-4 text-center">
          <Link href="/" className="text-sm text-muted-foreground hover:underline">
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  )
}

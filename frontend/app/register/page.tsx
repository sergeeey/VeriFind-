'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { BarChart3, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { useToast } from '@/components/ui/use-toast'

export default function RegisterPage() {
  const [copied, setCopied] = useState(false)
  const { toast } = useToast()
  const demoApiKey = 'sk-ape-demo-12345678901234567890'

  const copyApiKey = () => {
    navigator.clipboard.writeText(demoApiKey)
    setCopied(true)
    toast({
      title: 'Copied!',
      description: 'API key copied to clipboard',
    })
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="flex items-center justify-center gap-2 mb-8">
          <BarChart3 className="h-10 w-10 text-primary" />
          <h1 className="text-3xl font-bold">APE 2026</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Get Started with APE 2026</CardTitle>
            <CardDescription>
              Request API access for production-grade financial analysis
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Demo Key */}
            <div className="rounded-lg border bg-muted/50 p-4">
              <h3 className="font-semibold mb-2">Demo API Key</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Try APE 2026 with this demo key (limited queries):
              </p>
              <div className="flex gap-2">
                <code className="flex-1 bg-background px-3 py-2 rounded border text-sm">
                  {demoApiKey}
                </code>
                <Button size="icon" variant="outline" onClick={copyApiKey}>
                  {copied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Production Access */}
            <div>
              <h3 className="font-semibold mb-2">Production Access</h3>
              <p className="text-sm text-muted-foreground mb-4">
                For production use with unlimited queries, contact us:
              </p>
              <ul className="text-sm space-y-2 text-muted-foreground">
                <li>• Email: api@ape2026.com</li>
                <li>• Include your use case and expected query volume</li>
                <li>• API keys are provisioned within 24 hours</li>
              </ul>
            </div>

            {/* Pricing */}
            <div className="rounded-lg border bg-muted/50 p-4">
              <h3 className="font-semibold mb-2">Pricing</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Demo (10 queries/day)</span>
                  <span className="font-medium">Free</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pro (1000 queries/month)</span>
                  <span className="font-medium">$49/month</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Enterprise (unlimited)</span>
                  <span className="font-medium">Custom</span>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <Button asChild className="flex-1">
                <Link href="/login">
                  Try Demo Key
                </Link>
              </Button>
              <Button asChild variant="outline" className="flex-1">
                <a href="mailto:api@ape2026.com">
                  Request Production Access
                </a>
              </Button>
            </div>
          </CardContent>
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

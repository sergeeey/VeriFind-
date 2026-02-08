import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { BarChart3, ShieldCheck, Zap, TrendingUp } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold">APE 2026</h1>
          </div>
          <div className="flex gap-4">
            <Button asChild variant="ghost">
              <Link href="/login">Login</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="container py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-5xl font-bold tracking-tight mb-6">
            Financial Analysis with
            <br />
            <span className="text-primary">Zero Hallucination</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            APE 2026 guarantees mathematical accuracy. LLMs generate code, not numbers.
            Every conclusion is verifiable.
          </p>
          <div className="flex gap-4 justify-center">
            <Button asChild size="lg">
              <Link href="/dashboard">
                Start Analyzing
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/docs">
                Learn More
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container py-20 border-t">
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader>
              <ShieldCheck className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Zero Hallucination</CardTitle>
              <CardDescription>
                0.00% hallucination rate guaranteed through architectural enforcement
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <Zap className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Real-Time Validation</CardTitle>
              <CardDescription>
                Every fact verified through executable code in isolated sandbox
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <TrendingUp className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Multi-Perspective</CardTitle>
              <CardDescription>
                Bull, Bear, and Neutral agents debate every conclusion
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <BarChart3 className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Temporal Integrity</CardTitle>
              <CardDescription>
                100% protection against look-ahead bias in historical analysis
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Stats */}
      <section className="container py-20 border-t">
        <div className="grid gap-8 md:grid-cols-3 text-center">
          <div>
            <div className="text-5xl font-bold text-primary mb-2">0.00%</div>
            <div className="text-muted-foreground">Hallucination Rate</div>
          </div>
          <div>
            <div className="text-5xl font-bold text-primary mb-2">100%</div>
            <div className="text-muted-foreground">Temporal Adherence</div>
          </div>
          <div>
            <div className="text-5xl font-bold text-primary mb-2">&lt;5s</div>
            <div className="text-muted-foreground">Average Query Time</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-6 mt-20">
        <div className="container text-center text-sm text-muted-foreground">
          <p>© 2026 APE 2026. Built with Next.js, TypeScript, and shadcn/ui.</p>
        </div>
      </footer>
    </div>
  )
}

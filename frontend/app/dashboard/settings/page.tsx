import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function SettingsDashboardPage() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Runtime configuration references for dashboard connectivity.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Client Runtime</CardTitle>
          <CardDescription>Current frontend runtime targets.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="rounded border p-3">
            <div className="text-muted-foreground">NEXT_PUBLIC_API_URL</div>
            <div className="font-medium">{apiBase}</div>
          </div>
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Notes</div>
            <div>
              API key is managed in login flow; backend rate limiting and circuit-breaker states are visible in
              <span> </span>
              <span className="font-medium">Usage</span>.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

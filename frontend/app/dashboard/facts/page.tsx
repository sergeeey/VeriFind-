import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function FactsDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Verified Facts</h1>
        <p className="text-muted-foreground">Open a completed query to inspect fact-level evidence and provenance.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>How to inspect facts</CardTitle>
          <CardDescription>
            Facts are attached to completed analysis episodes and include confidence, source and code path.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button asChild>
            <Link href="/dashboard/activity">Open Activity</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/dashboard/query/new">Run New Query</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

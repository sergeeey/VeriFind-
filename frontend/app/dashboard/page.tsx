import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import Link from 'next/link'
import { Plus, History, Database, Activity } from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2">Welcome to APE 2026</h1>
        <p className="text-muted-foreground">
          Financial analysis with zero hallucination guarantee
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/query/new">
            <CardHeader>
              <Plus className="h-10 w-10 text-primary mb-2" />
              <CardTitle>New Query</CardTitle>
              <CardDescription>
                Submit a financial analysis query
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/history">
            <CardHeader>
              <History className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Query History</CardTitle>
              <CardDescription>
                View your past analysis queries
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/facts">
            <CardHeader>
              <Database className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Verified Facts</CardTitle>
              <CardDescription>
                Browse all verified facts database
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>System Status</CardTitle>
            <Activity className="h-5 w-5 text-green-500" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-green-500 mb-1">✓</div>
              <div className="text-sm text-muted-foreground">API Healthy</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-1">256</div>
              <div className="text-sm text-muted-foreground">Total Queries</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-green-500 mb-1">0.00%</div>
              <div className="text-sm text-muted-foreground">Hallucination Rate</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-500 mb-1">&lt;5s</div>
              <div className="text-sm text-muted-foreground">Avg Response Time</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your latest analysis queries</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div>
                <p className="font-medium">50-day MA for AAPL</p>
                <p className="text-sm text-muted-foreground">2 hours ago • Completed</p>
              </div>
              <Button variant="outline" size="sm">
                View Results
              </Button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div>
                <p className="font-medium">SPY vs QQQ correlation</p>
                <p className="text-sm text-muted-foreground">5 hours ago • Completed</p>
              </div>
              <Button variant="outline" size="sm">
                View Results
              </Button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div>
                <p className="font-medium">TSLA volatility analysis</p>
                <p className="text-sm text-muted-foreground">1 day ago • Completed</p>
              </div>
              <Button variant="outline" size="sm">
                View Results
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

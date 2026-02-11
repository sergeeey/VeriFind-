import { Button } from '@/components/ui/button'
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import Link from 'next/link'
import { Plus, History, Database, Activity, Microscope, Bell, Gauge, SlidersHorizontal, GitCompareArrows, Target } from 'lucide-react'
import { RecentActivityPanel } from '@/components/dashboard/RecentActivityPanel'
import { SystemStatusPanel } from '@/components/dashboard/SystemStatusPanel'

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

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/intelligence">
            <CardHeader>
              <Microscope className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Intelligence</CardTitle>
              <CardDescription>
                Unified view for SEC, sentiment, sensitivity and chart signals
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/alerts">
            <CardHeader>
              <Bell className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Alerts</CardTitle>
              <CardDescription>
                Create and monitor price threshold alerts
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/usage">
            <CardHeader>
              <Gauge className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Usage</CardTitle>
              <CardDescription>
                Inspect API key usage and rate-limit pressure
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/sensitivity">
            <CardHeader>
              <SlidersHorizontal className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Sensitivity</CardTitle>
              <CardDescription>
                Sweep price shocks and inspect PnL sign-flip behavior
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/calibration">
            <CardHeader>
              <Target className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Calibration</CardTitle>
              <CardDescription>
                Inspect confidence reliability curve, ECE and Brier score
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <Link href="/dashboard/compare">
            <CardHeader>
              <GitCompareArrows className="h-10 w-10 text-primary mb-2" />
              <CardTitle>Compare</CardTitle>
              <CardDescription>
                Compare the same analysis across multiple tickers
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>

      {/* System Status */}
      <SystemStatusPanel />

      {/* Recent Activity */}
      <RecentActivityPanel />
    </div>
  )
}

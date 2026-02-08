'use client'

import { useEffect, useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { ResultsHeader } from '@/components/results/ResultsHeader'
import { FactsTable } from '@/components/results/FactsTable'
import { DebateViewer } from '@/components/results/DebateViewer'
import { SynthesisCard } from '@/components/results/SynthesisCard'
import { CodeViewer } from '@/components/results/CodeViewer'
import { FactDetailsDialog } from '@/components/results/FactDetailsDialog'
import { ChartContainer } from '@/components/charts/ChartContainer'
import { TimeRangeSelector } from '@/components/charts/TimeRangeSelector'
import { CandlestickChart } from '@/components/charts/CandlestickChart'
import { ConfidenceTrendChart } from '@/components/charts/ConfidenceTrendChart'
import { DebateDistributionChart } from '@/components/charts/DebateDistributionChart'
import { ExecutionTimeHistogram } from '@/components/charts/ExecutionTimeHistogram'
import { FactTimelineChart } from '@/components/charts/FactTimelineChart'
import { api } from '@/lib/api'
import type { Episode } from '@/types/results'
import type { FactsTableRow } from '@/types/results'
import type { TimeRange } from '@/types/charts'
import { Download, ArrowLeft } from 'lucide-react'

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()

  const episodeId = params?.id as string

  const [episode, setEpisode] = useState<Episode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFact, setSelectedFact] = useState<FactsTableRow | null>(null)
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false)
  const [timeRange, setTimeRange] = useState<TimeRange>('1M')

  useEffect(() => {
    if (!episodeId) return

    const fetchEpisode = async () => {
      try {
        const response = await api.getEpisode(episodeId)
        const episodeData = response.data

        // Calculate duration if both timestamps exist
        if (episodeData.created_at && episodeData.completed_at) {
          const start = new Date(episodeData.created_at).getTime()
          const end = new Date(episodeData.completed_at).getTime()
          episodeData.duration_ms = end - start
        }

        setEpisode(episodeData)
        setError(null)
      } catch (err: any) {
        console.error('Failed to fetch episode:', err)
        setError(err.response?.data?.message || 'Failed to load results')
        toast({
          title: 'Error',
          description: 'Failed to load results',
          variant: 'destructive',
        })
      } finally {
        setLoading(false)
      }
    }

    fetchEpisode()
  }, [episodeId, toast])

  const handleViewCode = (fact: FactsTableRow) => {
    if (fact.source_code) {
      setSelectedCode(fact.source_code)
    } else {
      toast({
        title: 'No code available',
        description: 'Source code not available for this fact',
        variant: 'destructive',
      })
    }
  }

  const handleViewDetails = (fact: FactsTableRow) => {
    setSelectedFact(fact)
    setDetailsDialogOpen(true)
  }

  const handleExport = (format: 'json' | 'csv') => {
    if (!episode) return

    try {
      if (format === 'json') {
        const dataStr = JSON.stringify(episode, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `episode_${episodeId}.json`
        link.click()
        URL.revokeObjectURL(url)
      } else if (format === 'csv') {
        // Simple CSV export of facts
        const headers = ['Fact ID', 'Values', 'Confidence', 'Execution Time', 'Memory', 'Created At']
        const rows = episode.verified_facts.map((fact) => [
          fact.fact_id,
          JSON.stringify(fact.extracted_values),
          fact.confidence_score?.toString() || 'N/A',
          fact.execution_time_ms.toString(),
          fact.memory_used_mb.toString(),
          fact.created_at,
        ])

        const csv = [headers, ...rows].map((row) => row.join(',')).join('\n')
        const dataBlob = new Blob([csv], { type: 'text/csv' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `episode_${episodeId}.csv`
        link.click()
        URL.revokeObjectURL(url)
      }

      toast({
        title: 'Export successful',
        description: `Results exported as ${format.toUpperCase()}`,
      })
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'Failed to export results',
        variant: 'destructive',
      })
    }
  }

  // Prepare chart data (must be before early returns - React Hooks rules)
  const chartData = useMemo(() => {
    if (!episode) return null

    // Confidence Trend Data
    const confidenceData = episode.verified_facts.map((fact, idx) => ({
      time: new Date(fact.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      confidence: fact.confidence_score || 0.95,
    }))

    // Debate Distribution Data
    const debateData = episode.debate_reports
      ? [
          {
            name: 'Bull',
            value: episode.debate_reports.filter((d) => d.perspective === 'bull').length,
            fill: '#22c55e',
          },
          {
            name: 'Bear',
            value: episode.debate_reports.filter((d) => d.perspective === 'bear').length,
            fill: '#ef4444',
          },
          {
            name: 'Neutral',
            value: episode.debate_reports.filter((d) => d.perspective === 'neutral').length,
            fill: '#94a3b8',
          },
        ].filter((d) => d.value > 0)
      : []

    // Execution Time Histogram Data (buckets)
    const executionTimes = episode.verified_facts.map((f) => f.execution_time_ms)
    const maxTime = Math.max(...executionTimes, 1)
    const bucketCount = 10
    const bucketSize = maxTime / bucketCount
    const buckets = Array.from({ length: bucketCount }, (_, i) => {
      const start = i * bucketSize
      const end = (i + 1) * bucketSize
      const count = executionTimes.filter((t) => t >= start && t < end).length
      return {
        bucket: `${Math.round(start)}-${Math.round(end)}ms`,
        count,
      }
    }).filter((b) => b.count > 0)

    // Fact Timeline Data
    const factsByDate = episode.verified_facts.reduce(
      (acc, fact) => {
        const date = new Date(fact.created_at).toLocaleDateString('ru-RU')
        if (!acc[date]) acc[date] = []
        acc[date].push(fact)
        return acc
      },
      {} as Record<string, typeof episode.verified_facts>
    )

    const timelineData = Object.entries(factsByDate).map(([date, facts]) => ({
      date,
      count: facts.length,
    }))

    // Mock Candlestick Data (for demonstration)
    const candlestickData = Array.from({ length: 30 }, (_, i) => {
      const basePrice = 100
      const volatility = 5
      const timestamp = Math.floor(Date.now() / 1000) - (30 - i) * 86400
      const open = basePrice + (Math.random() - 0.5) * volatility
      const close = open + (Math.random() - 0.5) * volatility
      const high = Math.max(open, close) + Math.random() * 2
      const low = Math.min(open, close) - Math.random() * 2
      return { time: timestamp, open, high, low, close }
    })

    return {
      confidence: confidenceData,
      debate: debateData,
      executionTime: buckets,
      timeline: timelineData,
      candlestick: candlestickData,
    }
  }, [episode])

  const factsTableRows: FactsTableRow[] = episode
    ? episode.verified_facts.map((fact) => ({
        ...fact,
        confidence_score: fact.confidence_score || 0.95,
      }))
    : []

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-48" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !episode) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg text-muted-foreground">{error || 'Episode not found'}</p>
          <Button onClick={() => router.push('/dashboard')} className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => router.push('/dashboard')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => handleExport('json')}>
            <Download className="mr-2 h-4 w-4" />
            Export JSON
          </Button>
          <Button variant="outline" onClick={() => handleExport('csv')}>
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Episode Header */}
      <ResultsHeader episode={episode} />

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="facts">
            Verified Facts ({episode.verified_facts.length})
          </TabsTrigger>
          {episode.debate_reports && episode.debate_reports.length > 0 && (
            <TabsTrigger value="debate">Debate Analysis</TabsTrigger>
          )}
          <TabsTrigger value="charts">Charts & Analytics</TabsTrigger>
          {selectedCode && <TabsTrigger value="code">Source Code</TabsTrigger>}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {episode.synthesis && <SynthesisCard synthesis={episode.synthesis} />}

          {episode.verified_facts.length > 0 && (
            <FactsTable
              facts={factsTableRows.slice(0, 5)}
              onViewCode={handleViewCode}
              onViewDetails={handleViewDetails}
            />
          )}
        </TabsContent>

        {/* Facts Tab */}
        <TabsContent value="facts">
          <FactsTable
            facts={factsTableRows}
            onViewCode={handleViewCode}
            onViewDetails={handleViewDetails}
          />
        </TabsContent>

        {/* Debate Tab */}
        {episode.debate_reports && episode.debate_reports.length > 0 && (
          <TabsContent value="debate">
            <DebateViewer debates={episode.debate_reports} />
          </TabsContent>
        )}

        {/* Charts Tab */}
        <TabsContent value="charts" className="space-y-6">
          {chartData && (
            <>
              {/* Time Range Selector */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Analytics Dashboard</h3>
                <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
              </div>

              {/* Charts Grid */}
              <div className="grid gap-6 md:grid-cols-2">
                {/* Confidence Trend Chart */}
                <ChartContainer
                  title="Confidence Trend"
                  description="Confidence scores over time for verified facts"
                >
                  <ConfidenceTrendChart data={chartData.confidence} height={260} />
                </ChartContainer>

                {/* Debate Distribution Chart */}
                {chartData.debate.length > 0 && (
                  <ChartContainer
                    title="Debate Distribution"
                    description="Distribution of Bull, Bear, and Neutral perspectives"
                  >
                    <DebateDistributionChart data={chartData.debate} height={260} />
                  </ChartContainer>
                )}

                {/* Execution Time Histogram */}
                <ChartContainer
                  title="Execution Time Distribution"
                  description="Histogram of fact verification execution times"
                >
                  <ExecutionTimeHistogram data={chartData.executionTime} height={280} />
                </ChartContainer>

                {/* Fact Timeline Chart */}
                <ChartContainer
                  title="Fact Verification Timeline"
                  description="Number of verified facts over time"
                >
                  <FactTimelineChart data={chartData.timeline} height={280} />
                </ChartContainer>
              </div>

              {/* Full Width Candlestick Chart */}
              <ChartContainer
                title="Price Analysis (Demo)"
                description="Candlestick chart for financial time series data"
              >
                <CandlestickChart data={chartData.candlestick} height={320} />
              </ChartContainer>
            </>
          )}
        </TabsContent>

        {/* Code Tab */}
        {selectedCode && (
          <TabsContent value="code">
            <CodeViewer code={selectedCode} />
          </TabsContent>
        )}
      </Tabs>

      {/* Fact Details Dialog */}
      <FactDetailsDialog
        fact={selectedFact}
        open={detailsDialogOpen}
        onOpenChange={setDetailsDialogOpen}
      />
    </div>
  )
}

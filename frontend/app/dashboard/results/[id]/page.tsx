'use client'

import { useEffect, useState } from 'react'
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
import { api } from '@/lib/api'
import type { Episode } from '@/types/results'
import type { FactsTableRow } from '@/types/results'
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

  const factsTableRows: FactsTableRow[] = episode.verified_facts.map((fact) => ({
    ...fact,
    confidence_score: fact.confidence_score || 0.95,
  }))

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

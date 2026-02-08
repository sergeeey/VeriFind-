'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api'
import { EXAMPLE_QUERIES } from '@/lib/constants'
import { Lightbulb, Send, X } from 'lucide-react'

const MAX_QUERY_LENGTH = 1000

export function QueryBuilder() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  const handleSubmit = async () => {
    // Validation
    if (!query.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a query',
        variant: 'destructive',
      })
      return
    }

    if (query.length > MAX_QUERY_LENGTH) {
      toast({
        title: 'Error',
        description: `Query must be less than ${MAX_QUERY_LENGTH} characters`,
        variant: 'destructive',
      })
      return
    }

    setLoading(true)
    try {
      const response = await api.submitQuery(query)
      const { query_id } = response.data

      toast({
        title: 'Query Submitted',
        description: 'Redirecting to results...',
      })

      // Redirect to status page
      router.push(`/dashboard/query/${query_id}`)
    } catch (error: any) {
      console.error('Query submission failed:', error)
      toast({
        title: 'Submission Failed',
        description: error.response?.data?.message || 'Failed to submit query',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setQuery('')
    toast({
      title: 'Query Cleared',
      description: 'Textarea has been cleared',
    })
  }

  const loadExample = (exampleQuery: string) => {
    setQuery(exampleQuery)
    toast({
      title: 'Example Loaded',
      description: 'You can now modify and submit',
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Ctrl+Enter
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const remainingChars = MAX_QUERY_LENGTH - query.length

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {/* Main Query Builder */}
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Analysis Query</CardTitle>
          <CardDescription>
            Ask APE 2026 to analyze financial data with zero hallucination guarantee
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Example Selector */}
          <div className="flex items-center gap-2">
            <Select onValueChange={(value) => loadExample(value)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Load example query..." />
              </SelectTrigger>
              <SelectContent>
                {EXAMPLE_QUERIES.map((example, index) => (
                  <SelectItem key={index} value={example.query}>
                    <span className="font-medium">{example.label}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({example.category})
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Textarea */}
          <div className="space-y-2">
            <Textarea
              placeholder="e.g., Calculate the 50-day moving average for AAPL over the last 6 months"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={6}
              className="resize-none"
              disabled={loading}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Press Ctrl+Enter to submit</span>
              <span className={remainingChars < 100 ? 'text-warning' : ''}>
                {remainingChars} characters remaining
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleSubmit}
              disabled={!query.trim() || loading}
              className="flex-1"
            >
              <Send className="mr-2 h-4 w-4" />
              {loading ? 'Submitting...' : 'Submit Query'}
            </Button>
            <Button onClick={handleClear} variant="outline" disabled={!query || loading}>
              <X className="mr-2 h-4 w-4" />
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tips Sidebar */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            Tips
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <p className="font-medium">Be Specific</p>
            <p className="text-muted-foreground">
              Include ticker symbols, time ranges, and specific metrics
            </p>
          </div>
          <div>
            <p className="font-medium">Use Examples</p>
            <p className="text-muted-foreground">
              Select from dropdown to see properly formatted queries
            </p>
          </div>
          <div>
            <p className="font-medium">Check Units</p>
            <p className="text-muted-foreground">
              APE validates all numerical outputs for temporal consistency
            </p>
          </div>
          <div>
            <p className="font-medium">Zero Hallucination</p>
            <p className="text-muted-foreground">
              All calculations run in isolated sandbox with verification
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

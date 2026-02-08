'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useRouter } from 'next/navigation'
import { Clock, TrendingUp } from 'lucide-react'
import type { QueryHistoryItem } from '@/types/query'

// Mock data - replace with API call when backend is ready
const MOCK_HISTORY: QueryHistoryItem[] = [
  {
    id: 'q_001',
    text: 'Calculate 50-day MA for AAPL',
    time: '2 hours ago',
    status: 'completed',
  },
  {
    id: 'q_002',
    text: 'SPY vs QQQ correlation 2024',
    time: '5 hours ago',
    status: 'completed',
  },
  {
    id: 'q_003',
    text: 'TSLA 30-day volatility analysis',
    time: '1 day ago',
    status: 'failed',
  },
  {
    id: 'q_004',
    text: 'MSFT Sharpe ratio 2021-2024',
    time: '2 days ago',
    status: 'completed',
  },
  {
    id: 'q_005',
    text: 'NVDA beta vs SPY analysis',
    time: '3 days ago',
    status: 'completed',
  },
]

export function QueryHistory() {
  const router = useRouter()

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      case 'pending':
        return 'bg-gray-500'
      default:
        return 'bg-blue-500'
    }
  }

  const handleClick = (queryId: string) => {
    router.push(`/dashboard/query/${queryId}`)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Recent Queries
        </CardTitle>
        <CardDescription>Your analysis history</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {MOCK_HISTORY.map((item) => (
            <div
              key={item.id}
              onClick={() => handleClick(item.id)}
              className="group cursor-pointer rounded-lg border p-3 transition-colors hover:bg-muted"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 space-y-1">
                  <p className="line-clamp-2 text-sm font-medium group-hover:text-primary">
                    {item.text}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{item.time}</span>
                  </div>
                </div>
                <Badge className={`${getStatusColor(item.status)} flex-shrink-0 text-xs`}>
                  {item.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>

        {MOCK_HISTORY.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No queries yet. Submit your first analysis!
          </div>
        )}
      </CardContent>
    </Card>
  )
}

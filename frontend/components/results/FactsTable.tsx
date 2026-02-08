'use client'

import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getConfidenceColor, formatDateTime } from '@/lib/utils'
import type { FactsTableRow, TableSortConfig, SortDirection } from '@/types/results'
import { ArrowUpDown, ArrowUp, ArrowDown, Eye, Code } from 'lucide-react'

interface FactsTableProps {
  facts: FactsTableRow[]
  onViewCode?: (fact: FactsTableRow) => void
  onViewDetails?: (fact: FactsTableRow) => void
}

export function FactsTable({ facts, onViewCode, onViewDetails }: FactsTableProps) {
  const [sortConfig, setSortConfig] = useState<TableSortConfig>({
    key: 'created_at',
    direction: 'desc',
  })
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20

  // Sort facts
  const sortedFacts = [...facts].sort((a, b) => {
    const aValue = a[sortConfig.key]
    const bValue = b[sortConfig.key]

    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue
    }

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortConfig.direction === 'asc'
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }

    return 0
  })

  // Paginate
  const totalPages = Math.ceil(sortedFacts.length / pageSize)
  const paginatedFacts = sortedFacts.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const handleSort = (key: keyof FactsTableRow) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const getSortIcon = (key: keyof FactsTableRow) => {
    if (sortConfig.key !== key) {
      return <ArrowUpDown className="ml-2 h-4 w-4" />
    }
    return sortConfig.direction === 'asc' ? (
      <ArrowUp className="ml-2 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-2 h-4 w-4" />
    )
  }

  const getConfidenceBadge = (score: number) => {
    const color = getConfidenceColor(score)
    return (
      <Badge className={color}>
        {(score * 100).toFixed(0)}%
      </Badge>
    )
  }

  if (facts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Verified Facts</CardTitle>
          <CardDescription>No verified facts available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Verified Facts ({facts.length})</CardTitle>
        <CardDescription>All calculations verified through VEE Sandbox</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('created_at')}
                  className="h-8 p-0 hover:bg-transparent"
                >
                  Timestamp
                  {getSortIcon('created_at')}
                </Button>
              </TableHead>
              <TableHead>Extracted Values</TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('confidence_score')}
                  className="h-8 p-0 hover:bg-transparent"
                >
                  Confidence
                  {getSortIcon('confidence_score')}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('execution_time_ms')}
                  className="h-8 p-0 hover:bg-transparent"
                >
                  Exec Time
                  {getSortIcon('execution_time_ms')}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('memory_used_mb')}
                  className="h-8 p-0 hover:bg-transparent"
                >
                  Memory
                  {getSortIcon('memory_used_mb')}
                </Button>
              </TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedFacts.map((fact) => (
              <TableRow key={fact.fact_id}>
                <TableCell className="text-xs text-muted-foreground">
                  {formatDateTime(new Date(fact.created_at))}
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    {Object.entries(fact.extracted_values).map(([key, value]) => (
                      <div key={key} className="text-sm">
                        <span className="font-mono text-xs text-muted-foreground">{key}:</span>{' '}
                        <span className="font-medium">{value.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{getConfidenceBadge(fact.confidence_score)}</TableCell>
                <TableCell className="text-sm">{fact.execution_time_ms}ms</TableCell>
                <TableCell className="text-sm">{fact.memory_used_mb.toFixed(2)}MB</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {fact.source_code && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onViewCode?.(fact)}
                      >
                        <Code className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onViewDetails?.(fact)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {(currentPage - 1) * pageSize + 1} to{' '}
              {Math.min(currentPage * pageSize, facts.length)} of {facts.length} facts
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <div className="flex items-center gap-2">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(
                    (page) =>
                      page === 1 ||
                      page === totalPages ||
                      (page >= currentPage - 1 && page <= currentPage + 1)
                  )
                  .map((page, index, array) => (
                    <>
                      {index > 0 && array[index - 1] !== page - 1 && (
                        <span key={`ellipsis-${page}`} className="px-2">
                          ...
                        </span>
                      )}
                      <Button
                        key={page}
                        variant={currentPage === page ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </Button>
                    </>
                  ))}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

'use client'

import { Button } from '@/components/ui/button'
import type { TimeRange } from '@/types/charts'

const RANGES: TimeRange[] = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

interface TimeRangeSelectorProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {RANGES.map((range) => (
        <Button
          key={range}
          type="button"
          size="sm"
          variant={value === range ? 'default' : 'outline'}
          onClick={() => onChange(range)}
        >
          {range}
        </Button>
      ))}
    </div>
  )
}

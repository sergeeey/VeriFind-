import React from 'react'

export const Progress = ({ value, className }: { value: number; className?: string }) => (
  <div data-testid="progress" data-value={value} className={className}>
    Progress: {value}%
  </div>
)

import React from 'react'

interface CardProps {
  children?: React.ReactNode
  className?: string
}

export const Card = ({ children, className }: CardProps) => (
  <div data-testid="card" className={className}>{children}</div>
)

export const CardHeader = ({ children, className }: CardProps) => (
  <div data-testid="card-header" className={className}>{children}</div>
)

export const CardTitle = ({ children, className }: CardProps) => (
  <div data-testid="card-title" className={className}>{children}</div>
)

export const CardDescription = ({ children, className }: CardProps) => (
  <div data-testid="card-description" className={className}>{children}</div>
)

export const CardContent = ({ children, className }: CardProps) => (
  <div data-testid="card-content" className={className}>{children}</div>
)

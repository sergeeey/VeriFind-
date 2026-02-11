import React from 'react'

export const Alert = ({ children, variant, className }: any) => (
  <div data-testid="alert" data-variant={variant} className={className}>
    {children}
  </div>
)

export const AlertDescription = ({ children }: any) => (
  <div data-testid="alert-description">{children}</div>
)

export const AlertTitle = ({ children }: any) => (
  <div data-testid="alert-title">{children}</div>
)

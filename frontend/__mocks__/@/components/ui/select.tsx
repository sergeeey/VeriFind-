import React from 'react'

interface SelectProps {
  children?: React.ReactNode
  value?: string
  onValueChange?: (value: string) => void
}

export const Select = ({ children, value, onValueChange }: SelectProps) => (
  <div data-testid="select" data-value={value}>{children}</div>
)

interface SelectContentProps {
  children?: React.ReactNode
}

export const SelectContent = ({ children }: SelectContentProps) => (
  <div data-testid="select-content">{children}</div>
)

interface SelectItemProps {
  children?: React.ReactNode
  value?: string
  disabled?: boolean
}

export const SelectItem = ({ children, value, disabled }: SelectItemProps) => (
  <div data-testid="select-item" data-value={value} data-disabled={disabled}>{children}</div>
)

interface SelectTriggerProps {
  children?: React.ReactNode
  className?: string
}

export const SelectTrigger = ({ children, className }: SelectTriggerProps) => (
  <div data-testid="select-trigger" className={className}>{children}</div>
)

interface SelectValueProps {
  placeholder?: string
}

export const SelectValue = ({ placeholder }: SelectValueProps) => (
  <span data-testid="select-value">{placeholder}</span>
)

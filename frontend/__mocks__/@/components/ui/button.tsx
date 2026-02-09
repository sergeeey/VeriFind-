import React from 'react'

interface ButtonProps {
  children?: React.ReactNode
  className?: string
  variant?: string
  size?: string
  onClick?: () => void
  disabled?: boolean
}

export const Button = ({ children, className, variant, size, onClick, disabled }: ButtonProps) => (
  <button 
    data-testid="button" 
    data-variant={variant}
    data-size={size}
    className={className}
    onClick={onClick}
    disabled={disabled}
  >
    {children}
  </button>
)

import React from 'react'

export const Input = React.forwardRef<HTMLInputElement, any>(
  ({ className, ...props }, ref) => (
    <input data-testid="input" ref={ref} className={className} {...props} />
  )
)
Input.displayName = 'Input'

import React from 'react'

export const Textarea = React.forwardRef<HTMLTextAreaElement, any>(
  ({ className, ...props }, ref) => (
    <textarea data-testid="textarea" ref={ref} className={className} {...props} />
  )
)
Textarea.displayName = 'Textarea'

import React from 'react'

export const Label = ({ children, htmlFor, className }: any) => (
  <label data-testid="label" htmlFor={htmlFor} className={className}>
    {children}
  </label>
)

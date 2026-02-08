import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format date to human-readable string
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Format duration in milliseconds to human-readable
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
  return `${(ms / 3600000).toFixed(1)}h`
}

// Format number with thousands separator
export function formatNumber(num: number, decimals: number = 2): string {
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// Format percentage
export function formatPercent(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`
}

// Truncate string with ellipsis
export function truncate(str: string, length: number): string {
  return str.length > length ? str.slice(0, length) + '...' : str
}

// Get confidence color based on score
export function getConfidenceColor(score: number): string {
  if (score >= 0.8) return 'text-green-500'
  if (score >= 0.6) return 'text-yellow-500'
  if (score >= 0.4) return 'text-orange-500'
  return 'text-red-500'
}

// Get confidence badge variant
export function getConfidenceBadgeVariant(
  score: number
): 'default' | 'secondary' | 'destructive' {
  if (score >= 0.7) return 'default'
  if (score >= 0.4) return 'secondary'
  return 'destructive'
}

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Copy to clipboard
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    return false
  }
}

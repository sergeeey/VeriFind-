'use client'

import { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Copy, Check, Code2 } from 'lucide-react'

interface CodeViewerProps {
  code: string
  language?: string
  title?: string
}

export function CodeViewer({ code, language = 'python', title = 'Source Code' }: CodeViewerProps) {
  const [copied, setCopied] = useState(false)
  const [highlighted, setHighlighted] = useState<string>('')
  const codeRef = useRef<HTMLElement>(null)
  const { toast } = useToast()

  useEffect(() => {
    // Simple syntax highlighting fallback (without Prism.js dependency)
    // In production, you would import Prism.js here
    const highlightCode = () => {
      let result = code

      // Python-style comments
      result = result.replace(/(#.*$)/gm, '<span style="color: #6a9955;">$1</span>')

      // Python keywords
      const keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'as', 'in', 'and', 'or', 'not', 'None', 'True', 'False']
      keywords.forEach(keyword => {
        const regex = new RegExp(`\\b(${keyword})\\b`, 'g')
        result = result.replace(regex, '<span style="color: #569cd6;">$1</span>')
      })

      // Strings
      result = result.replace(/(['"`])(.*?)\1/g, '<span style="color: #ce9178;">$1$2$1</span>')

      // Numbers
      result = result.replace(/\b(\d+\.?\d*)\b/g, '<span style="color: #b5cea8;">$1</span>')

      // Function names
      result = result.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g, '<span style="color: #dcdcaa;">$1</span>(')

      setHighlighted(result)
    }

    highlightCode()
  }, [code])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      toast({
        title: 'Copied!',
        description: 'Code copied to clipboard',
      })
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy code to clipboard',
        variant: 'destructive',
      })
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="h-5 w-5" />
            <CardTitle>{title}</CardTitle>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="gap-2"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                Copy
              </>
            )}
          </Button>
        </div>
        <CardDescription>Verified code executed in VEE Sandbox</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
            <code
              ref={codeRef}
              className="language-python"
              dangerouslySetInnerHTML={{ __html: highlighted }}
            />
          </pre>
          {code.split('\n').length > 1 && (
            <div className="mt-2 text-xs text-muted-foreground">
              {code.split('\n').length} lines
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

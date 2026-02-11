import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const docsLinks = [
  { href: '/dashboard/intelligence', label: 'Intelligence Workbench', description: 'SEC, sentiment and chart signal workflows.' },
  { href: '/dashboard/sensitivity', label: 'Sensitivity Workbench', description: 'Price shock and sign-flip analysis.' },
  { href: '/dashboard/compare', label: 'Compare Workbench', description: 'Parallel multi-ticker comparative analysis.' },
  { href: '/dashboard/calibration', label: 'Calibration Workbench', description: 'Confidence reliability and ECE diagnostics.' },
]

export default function DocsDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Docs</h1>
        <p className="text-muted-foreground">Operational entry points for the current dashboard modules.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {docsLinks.map((item) => (
          <Card key={item.href}>
            <CardHeader>
              <CardTitle className="text-xl">{item.label}</CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Link className="text-sm text-primary underline underline-offset-4" href={item.href}>
                Open module
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

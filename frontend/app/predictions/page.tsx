import { PredictionDashboard } from '@/components/predictions'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Predictions | VeriFind',
  description: 'Track prediction accuracy and performance metrics',
}

export default function PredictionsPage() {
  return <PredictionDashboard />
}

"use client"

import { Badge } from "@/components/ui/badge"
import { TrendingUp, Activity } from "lucide-react"

type BreakoutAlert = {
  player: string
  position: string
  team: string
  category: string
  signal: string
  confidence: number
  stats: string[]
}

interface BreakoutDetectorTableProps {
  alerts: BreakoutAlert[]
}

export function BreakoutDetectorTable({ alerts }: BreakoutDetectorTableProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Activity className="h-5 w-5 text-orange-600" />
          Breakout Detector
        </h2>
        <Badge variant="secondary">{alerts.length} alerts</Badge>
      </div>

      {alerts.length === 0 ? (
        <div className="rounded-md border bg-card p-8 text-center text-muted-foreground">
          No breakout signals detected
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert, i) => {
            // Parse all stats dynamically
            const statMap: Record<string, string> = {}
            alert.stats.forEach(stat => {
              const [metric, change] = stat.split(':').map(s => s.trim())
              if (metric && change) {
                statMap[metric] = change
              }
            })
            
            return (
              <div 
                key={i} 
                className="rounded-lg border bg-card hover:bg-accent/50 transition-colors p-4"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-lg">{alert.player}</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {alert.position} • {alert.team}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-orange-600">
                      {alert.confidence}%
                    </div>
                    <div className="text-xs text-muted-foreground">confidence</div>
                  </div>
                </div>

                {/* Dynamic Metrics Grid */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    Key Indicators
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(statMap).map(([key, value]) => (
                      <div key={key} className="rounded bg-muted/50 p-2">
                        <div className="text-xs text-muted-foreground capitalize">
                          {key.replace(/_/g, ' ').replace('percent', '%').replace('avg', '')}
                        </div>
                        <div className={`font-bold ${
                          value.startsWith('+') 
                            ? 'text-green-600' 
                            : value.startsWith('-') 
                              ? 'text-red-600' 
                              : 'text-foreground'
                        }`}>
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

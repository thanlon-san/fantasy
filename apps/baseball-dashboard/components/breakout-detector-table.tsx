"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Activity, PlusCircle, UserCheck } from "lucide-react"
import Link from "next/link"

type BreakoutAlert = {
  player: string
  position: string
  team: string
  category: string
  signal: string
  confidence: number
  stats: string[]
  is_free_agent?: boolean
}

interface BreakoutDetectorTableProps {
  alerts: BreakoutAlert[]
}

const SIGNAL_STYLES: Record<string, { badge: string; border: string; glow: string }> = {
  STRONG:   { badge: "bg-orange-500 text-white", border: "border-orange-500/40", glow: "shadow-orange-500/10" },
  EMERGING: { badge: "bg-amber-500 text-white",  border: "border-amber-500/30",  glow: "shadow-amber-500/10"  },
  WATCH:    { badge: "bg-slate-500 text-white",   border: "border-slate-500/20",  glow: "" },
  FADING:   { badge: "bg-rose-500 text-white",    border: "border-rose-500/30",   glow: "" },
}

export function BreakoutDetectorTable({ alerts }: BreakoutDetectorTableProps) {
  const [filter, setFilter] = useState<"add" | "all">("add")

  const faAlerts = alerts.filter(a => a.is_free_agent !== false)
  const rosterAlerts = alerts.filter(a => a.is_free_agent === false)
  const visibleAlerts = filter === "add" ? faAlerts : alerts

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Activity className="h-5 w-5 text-orange-600" />
          Breakout Detector
        </h2>
        <div className="flex items-center gap-2">
          {/* Tab switcher */}
          <div className="flex rounded-lg border bg-muted p-0.5 text-xs font-medium">
            <button
              onClick={() => setFilter("add")}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 transition-colors ${
                filter === "add"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <PlusCircle className="h-3 w-3" />
              Add ({faAlerts.length})
            </button>
            <button
              onClick={() => setFilter("all")}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 transition-colors ${
                filter === "all"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <UserCheck className="h-3 w-3" />
              All ({alerts.length})
            </button>
          </div>
        </div>
      </div>

      {visibleAlerts.length === 0 ? (
        <div className="rounded-md border bg-card p-8 text-center text-muted-foreground">
          {filter === "add"
            ? "No free agent breakout signals detected yet — check back after more games."
            : "No breakout signals detected."}
        </div>
      ) : (
        <div className="space-y-3">
          {visibleAlerts.map((alert) => {
            const isFa = alert.is_free_agent !== false
            const styles = SIGNAL_STYLES[alert.signal] ?? SIGNAL_STYLES.WATCH
            const statMap: Record<string, string> = {}
            alert.stats.forEach(stat => {
              const [metric, change] = stat.split(':').map(s => s.trim())
              if (metric && change) statMap[metric] = change
            })

            return (
              <div
                key={alert.player}
                className={`rounded-lg border bg-card hover:bg-accent/50 transition-colors p-4 shadow-sm ${styles.border} ${styles.glow}`}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3 gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/player?name=${encodeURIComponent(alert.player)}`}
                        className="font-bold text-base hover:underline leading-tight"
                      >
                        {alert.player}
                      </Link>
                      <Badge className={`text-[10px] px-1.5 py-0 shrink-0 ${styles.badge}`}>
                        {alert.signal}
                      </Badge>
                      {isFa ? (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0 border-emerald-500/50 text-emerald-500 bg-emerald-500/10">
                          + Add
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0 text-muted-foreground">
                          On Roster
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {alert.position} · {alert.team} · {alert.category}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xl font-bold text-orange-500 tabular-nums">
                      {alert.confidence}%
                    </div>
                    <div className="text-[10px] text-muted-foreground">confidence</div>
                  </div>
                </div>

                {/* Metrics */}
                {Object.keys(statMap).length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Key Indicators
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(statMap).map(([key, value]) => (
                        <div key={key} className="rounded bg-muted/60 px-2 py-1 text-xs">
                          <span className="text-muted-foreground capitalize mr-1">
                            {key.replace(/_/g, ' ').replace('percent', '%').replace(' avg', '')}:
                          </span>
                          <span className={`font-semibold tabular-nums ${
                            value.startsWith('+') ? 'text-emerald-500'
                            : value.startsWith('-') ? 'text-rose-500'
                            : 'text-foreground'
                          }`}>
                            {value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {filter === "add" && rosterAlerts.length > 0 && (
        <p className="text-xs text-muted-foreground text-center pt-1">
          +{rosterAlerts.length} breakout signal{rosterAlerts.length > 1 ? "s" : ""} on your roster — switch to All to view
        </p>
      )}
    </div>
  )
}

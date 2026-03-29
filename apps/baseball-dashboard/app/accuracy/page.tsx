"use client"

import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Activity, Target, TrendingUp, ArrowLeft, BarChart3, Zap, AlertTriangle } from "lucide-react"
import Link from "next/link"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts"

import type { AccuracyReport } from "@fantasy/types"
import { AccuracyReportSchema } from "@fantasy/types"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type AccuracyData = AccuracyReport

const TIER_ORDER = ["MUST_START", "START", "FLEX", "BENCH", "AVOID"]
const TIER_COLORS: Record<string, string> = {
  MUST_START: "#10b981",
  START: "#3b82f6",
  FLEX: "#f59e0b",
  BENCH: "#94a3b8",
  AVOID: "#ef4444",
}
const SIGNAL_COLORS: Record<string, string> = {
  STRONG: "#10b981",
  EMERGING: "#3b82f6",
  WATCH: "#f59e0b",
  FADING: "#ef4444",
}

export default function AccuracyPage() {
  const { data, isLoading, error } = useQuery<AccuracyData>({
    queryKey: ["accuracy"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/accuracy`, { cache: "no-store" })
      if (!res.ok) throw new Error("Failed to fetch accuracy data")
      return AccuracyReportSchema.parse(await res.json())
    },
    refetchInterval: 120_000,
  })

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="container mx-auto px-4 py-8 max-w-5xl">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-700/40 rounded w-64" />
            <div className="h-64 bg-slate-700/40 rounded" />
          </div>
        </div>
      </main>
    )
  }

  const lineup = data?.lineup ?? { total: 0, correct: 0, accuracy: 0, by_tier: {} }
  const breakout = data?.breakout ?? { total: 0, correct: 0, accuracy: 0, by_signal: {} }
  const recentBreakouts = data?.recent_breakout_predictions ?? []
  const waiverCount = data?.waiver_transaction_count ?? 0

  const tierChartData = TIER_ORDER
    .filter(t => lineup.by_tier[t])
    .map(t => ({
      name: t.replace("_", " "),
      accuracy: lineup.by_tier[t].accuracy,
      total: lineup.by_tier[t].total,
      tier: t,
    }))

  const signalChartData = Object.entries(breakout.by_signal).map(([sig, stats]) => ({
    name: sig,
    accuracy: stats.accuracy,
    total: stats.total,
    signal: sig,
  }))

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <header className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="text-slate-400 hover:text-slate-200">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
              <Target className="h-6 w-6 text-emerald-400" />
              Prediction Accuracy
            </h1>
          </div>
          <p className="text-muted-foreground text-sm">
            Track how well the optimizer, breakout detector, and waiver recommendations perform over time.
          </p>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            No accuracy data yet. Data will populate as the season progresses and predictions are tracked.
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-4">
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-400 uppercase tracking-wide">
              <Activity className="h-3.5 w-3.5" />
              Lineup Accuracy
            </div>
            <div className="text-2xl font-bold">
              {lineup.total > 0 ? `${lineup.accuracy}%` : "—"}
            </div>
            <div className="text-xs text-slate-500">{lineup.total} predictions</div>
          </div>

          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-4">
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-400 uppercase tracking-wide">
              <Zap className="h-3.5 w-3.5" />
              Breakout Accuracy
            </div>
            <div className="text-2xl font-bold">
              {breakout.total > 0 ? `${breakout.accuracy}%` : "—"}
            </div>
            <div className="text-xs text-slate-500">{breakout.total} tracked</div>
          </div>

          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-4">
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-400 uppercase tracking-wide">
              <TrendingUp className="h-3.5 w-3.5" />
              Waiver Moves
            </div>
            <div className="text-2xl font-bold">{waiverCount}</div>
            <div className="text-xs text-slate-500">last 90 days</div>
          </div>

          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-4">
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-400 uppercase tracking-wide">
              <BarChart3 className="h-3.5 w-3.5" />
              Total Predictions
            </div>
            <div className="text-2xl font-bold">{lineup.total + breakout.total}</div>
            <div className="text-xs text-slate-500">all time</div>
          </div>
        </div>

        {/* Lineup Accuracy by Tier */}
        {tierChartData.length > 0 && (
          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-5 mb-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-400" />
              Lineup Accuracy by Tier
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tierChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 8 }}
                    labelStyle={{ color: "#e2e8f0" }}
                    formatter={(value, _name, entry) => {
                      const total = (entry as { payload?: { total?: number } })?.payload?.total ?? 0
                      return [`${value}% (${total} predictions)`, "Accuracy"]
                    }}
                  />
                  <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                    {tierChartData.map((entry) => (
                      <Cell key={entry.tier} fill={TIER_COLORS[entry.tier] ?? "#64748b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Breakout Accuracy by Signal */}
        {signalChartData.length > 0 && (
          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-5 mb-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-emerald-400" />
              Breakout Accuracy by Signal
            </h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={signalChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 8 }}
                    labelStyle={{ color: "#e2e8f0" }}
                  />
                  <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                    {signalChartData.map((entry) => (
                      <Cell key={entry.signal} fill={SIGNAL_COLORS[entry.signal] ?? "#64748b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Recent Breakout Predictions */}
        {recentBreakouts.length > 0 && (
          <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-5">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-amber-400" />
              Recent Breakout Predictions
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400 uppercase tracking-wide border-b border-slate-700/60">
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2 pr-4">Player</th>
                    <th className="pb-2 pr-4">Signal</th>
                    <th className="pb-2 pr-4">Confidence</th>
                    <th className="pb-2 pr-4">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {recentBreakouts.slice(0, 20).map((p, i) => (
                    <tr key={`${p.player_name}-${p.date}-${i}`} className="text-slate-300">
                      <td className="py-2 pr-4 text-slate-500">{p.date}</td>
                      <td className="py-2 pr-4 font-medium">
                        <Link href={`/player/${encodeURIComponent(p.player_name)}`} className="hover:text-emerald-400">
                          {p.player_name}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">
                        <Badge variant={p.signal === "STRONG" ? "default" : "secondary"} className="text-[10px]">
                          {p.signal}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">{p.confidence.toFixed(0)}%</td>
                      <td className="py-2 pr-4">
                        {p.was_successful === null ? (
                          <span className="text-slate-500">Pending</span>
                        ) : p.was_successful ? (
                          <span className="text-emerald-400 font-semibold">Hit</span>
                        ) : (
                          <span className="text-red-400">Miss</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {lineup.total === 0 && breakout.total === 0 && !error && (
          <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed border-slate-700/60">
            <Target className="h-16 w-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium mb-2">No prediction data yet</p>
            <p className="text-sm">
              Accuracy tracking begins when the season starts and predictions are logged daily.
            </p>
          </div>
        )}
      </div>
    </main>
  )
}

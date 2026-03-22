"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { ArrowLeft, RefreshCw, TrendingUp, TrendingDown, Minus, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

// ─── Types ────────────────────────────────────────────────────────────────────

type CategoryData = {
  name: string
  label: string
  group: "batting" | "pitching"
  better: "high" | "low"
  weekly_ranks: (number | null)[]
  weekly_values: (number | null)[]
  trend: "improving" | "declining" | "stable" | "neutral"
  avg_rank: number | null
}

type TrajectoryData = {
  current_week: number
  categories: Record<string, CategoryData>
  summary: {
    dominating: string[]
    struggling: string[]
    improving: string[]
  }
}

// ─── Sparkline ────────────────────────────────────────────────────────────────

function Sparkline({ ranks, width = 80, height = 28 }: { ranks: (number | null)[]; width?: number; height?: number }) {
  const valid = ranks.map((r, i) => ({ r, i })).filter(x => x.r !== null) as { r: number; i: number }[]
  if (valid.length === 0) {
    return <div className="text-slate-600 text-xs italic">No data</div>
  }

  const maxRank = 12
  const minRank = 1
  const xStep = valid.length > 1 ? width / (valid.length - 1) : width / 2
  const yOf = (r: number) => ((r - minRank) / (maxRank - minRank)) * height

  const points = valid.map((x, i) => `${i * xStep},${yOf(x.r)}`).join(" ")
  const lastRank = valid[valid.length - 1].r

  const color = lastRank <= 4 ? "#34d399" : lastRank <= 8 ? "#fbbf24" : "#f87171"

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {valid.map((x, i) => (
        <circle key={i} cx={i * xStep} cy={yOf(x.r)} r={2} fill={color} />
      ))}
    </svg>
  )
}

// ─── Category Card ────────────────────────────────────────────────────────────

function CategoryCard({ sid, cat }: { sid: string; cat: CategoryData }) {
  const avgRank = cat.avg_rank
  const rankColor =
    avgRank === null ? "text-slate-500"
    : avgRank <= 4   ? "text-emerald-400"
    : avgRank <= 8   ? "text-amber-400"
    : "text-red-400"

  const TrendIcon =
    cat.trend === "improving" ? TrendingUp
    : cat.trend === "declining" ? TrendingDown
    : Minus

  const trendColor =
    cat.trend === "improving" ? "text-emerald-400"
    : cat.trend === "declining" ? "text-red-400"
    : "text-slate-500"

  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-900/60 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-bold text-sm text-slate-100">{cat.name}</div>
          <div className="text-[10px] text-slate-500">{cat.label}</div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-black ${rankColor}`}>
            {avgRank !== null ? `#${avgRank}` : "—"}
          </div>
          <div className="text-[10px] text-slate-500">avg rank</div>
        </div>
      </div>

      <Sparkline ranks={cat.weekly_ranks} />

      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
          <TrendIcon className="h-3 w-3" />
          <span className="capitalize">{cat.trend}</span>
        </div>
        <div className="text-[10px] text-slate-600">
          {cat.group === "batting" ? "BAT" : "PIT"} · better={cat.better}
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TrajectoryPage() {
  const [data, setData] = useState<TrajectoryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetch_ = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/season/trajectory`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      setData(await res.json())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach server")
    } finally {
      setLoading(false)
      if (showRefresh) setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetch_()
    const t = setInterval(() => fetch_(), 60_000)
    return () => clearInterval(t)
  }, [fetch_])

  if (loading) return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-500 animate-pulse text-sm">Loading trajectory…</div>
    </main>
  )

  if (error || !data) return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-slate-600 mx-auto" />
        <div className="text-slate-400">{error ?? "No data"}</div>
        <div className="text-slate-600 text-xs font-mono">python scripts/draft_server.py</div>
        <Button size="sm" variant="outline" onClick={() => fetch_(true)}>Retry</Button>
      </div>
    </main>
  )

  const battingCats = Object.entries(data.categories).filter(([, c]) => c.group === "batting")
  const pitchingCats = Object.entries(data.categories).filter(([, c]) => c.group === "pitching")
  const { dominating, struggling, improving } = data.summary

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/"><Button variant="ghost" size="sm" className="text-slate-500 gap-1.5"><ArrowLeft className="h-4 w-4" />Dashboard</Button></Link>
            <div className="h-4 border-r border-slate-700" />
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              <span className="font-bold text-lg">Category Trajectory</span>
              <span className="text-slate-500 text-sm">Week {data.current_week}</span>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => fetch_(true)} disabled={refreshing}>
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Summary */}
        {(dominating.length > 0 || struggling.length > 0 || improving.length > 0) && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5 space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Season Summary</div>
            <div className="flex flex-wrap gap-2 text-sm">
              {dominating.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500">Dominating:</span>
                  {dominating.map(n => <Badge key={n} className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">{n}</Badge>)}
                </div>
              )}
              {struggling.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500">Struggling:</span>
                  {struggling.map(n => <Badge key={n} className="bg-red-500/20 text-red-400 border-red-500/30">{n}</Badge>)}
                </div>
              )}
              {improving.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500">Improving:</span>
                  {improving.map(n => <Badge key={n} className="bg-amber-500/20 text-amber-400 border-amber-500/30">{n}</Badge>)}
                </div>
              )}
            </div>
            <div className="text-[10px] text-slate-600">
              Rank colors: <span className="text-emerald-400">green = top 4</span> · <span className="text-amber-400">yellow = 5–8</span> · <span className="text-red-400">red = 9–12</span>
            </div>
          </div>
        )}

        {/* Batting */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <TrendingUp className="h-3.5 w-3.5" /> Batting Categories
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {battingCats.map(([sid, cat]) => (
              <CategoryCard key={sid} sid={sid} cat={cat} />
            ))}
          </div>
        </section>

        {/* Pitching */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <TrendingDown className="h-3.5 w-3.5" /> Pitching Categories
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {pitchingCats.map(([sid, cat]) => (
              <CategoryCard key={sid} sid={sid} cat={cat} />
            ))}
          </div>
        </section>

        <footer className="text-center text-xs text-slate-600 pb-4">
          Updated from Yahoo every 60s · Ranks cached for 1 hour
        </footer>
      </div>
    </main>
  )
}

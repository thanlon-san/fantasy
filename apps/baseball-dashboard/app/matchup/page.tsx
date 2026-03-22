"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { ArrowLeft, RefreshCw, TrendingUp, TrendingDown, Minus, AlertTriangle, Swords } from "lucide-react"
import { Button } from "@/components/ui/button"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

// ─── Types ────────────────────────────────────────────────────────────────────

type CategoryStatus = "win" | "close_win" | "loss" | "close_loss" | "tied" | "unknown"

type Category = {
  stat_id:   string
  name:      string
  label:     string
  group:     "batting" | "pitching"
  better:    "high" | "low"
  my_value:  number | null
  opp_value: number | null
  status:    CategoryStatus
}

type MatchupData = {
  week:       number
  week_start: string | null
  week_end:   string | null
  status:     string
  my_team:    string | null
  opp_team:   string | null
  categories: Category[]
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function statusConfig(s: CategoryStatus) {
  switch (s) {
    case "win":        return { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", label: "WIN",      icon: "↑", dot: "bg-emerald-400" }
    case "close_win":  return { bg: "bg-emerald-500/5",  border: "border-emerald-500/20", text: "text-emerald-300", label: "CLOSE ↑",  icon: "↗", dot: "bg-emerald-300" }
    case "loss":       return { bg: "bg-red-500/10",     border: "border-red-500/30",     text: "text-red-400",     label: "LOSS",     icon: "↓", dot: "bg-red-400"     }
    case "close_loss": return { bg: "bg-amber-500/10",   border: "border-amber-500/30",   text: "text-amber-400",   label: "CLOSE ↓",  icon: "↘", dot: "bg-amber-400"   }
    case "tied":       return { bg: "bg-slate-700/30",   border: "border-slate-600",      text: "text-slate-400",   label: "TIED",     icon: "–", dot: "bg-slate-500"   }
    default:           return { bg: "bg-slate-800/30",   border: "border-slate-700",      text: "text-slate-500",   label: "–",        icon: "?", dot: "bg-slate-700"   }
  }
}

function formatVal(val: number | null, name: string): string {
  if (val === null || val === undefined) return "–"
  if (name === "ERA" || name === "WHIP" || name === "OPS") return val.toFixed(3)
  return val.toString()
}

function scoreSummary(cats: Category[]): { wins: number; losses: number; close: number } {
  let wins = 0, losses = 0, close = 0
  for (const c of cats) {
    if (c.status === "win")        wins++
    else if (c.status === "loss")  losses++
    else if (c.status === "close_win" || c.status === "close_loss") close++
  }
  return { wins, losses, close }
}

// ─── Components ───────────────────────────────────────────────────────────────

function CategoryRow({ cat, myName, oppName }: { cat: Category; myName: string; oppName: string }) {
  const cfg     = statusConfig(cat.status)
  const isSwing = cat.status === "close_win" || cat.status === "close_loss"

  return (
    <div className={`flex items-center gap-3 px-4 py-3 border rounded-lg ${cfg.bg} ${cfg.border} ${isSwing ? "ring-1 ring-amber-500/20" : ""}`}>
      {/* Status dot */}
      <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />

      {/* Category name */}
      <div className="w-24 shrink-0">
        <div className="font-bold text-sm text-slate-100">{cat.name}</div>
        <div className="text-[10px] text-slate-500">{cat.label}</div>
      </div>

      {/* My value */}
      <div className="flex-1 text-right">
        <div className="text-sm font-mono font-semibold text-slate-100">{formatVal(cat.my_value, cat.name)}</div>
        <div className="text-[10px] text-slate-500 truncate">{myName}</div>
      </div>

      {/* vs */}
      <div className={`text-sm font-bold w-8 text-center ${cfg.text}`}>{cfg.icon}</div>

      {/* Their value */}
      <div className="flex-1 text-left">
        <div className="text-sm font-mono font-semibold text-slate-300">{formatVal(cat.opp_value, cat.name)}</div>
        <div className="text-[10px] text-slate-500 truncate">{oppName}</div>
      </div>

      {/* Status badge */}
      <div className={`text-[10px] font-bold w-16 text-right shrink-0 ${cfg.text}`}>
        {isSwing ? <span className="text-amber-400">⚠ SWING</span> : cfg.label}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MatchupPage() {
  const [data,      setData]      = useState<MatchupData | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [refreshing,setRefreshing] = useState(false)

  const fetch_ = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/season/matchup`, { cache: "no-store" })
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
      <div className="text-slate-500 animate-pulse text-sm">Loading matchup…</div>
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

  const batting  = data.categories.filter(c => c.group === "batting")
  const pitching = data.categories.filter(c => c.group === "pitching")
  const summary  = scoreSummary(data.categories)
  const myName   = data.my_team  ?? "2balls"
  const oppName  = data.opp_team ?? "Opponent"
  const isPre    = data.status === "preevent" || data.categories.every(c => c.status === "unknown" || c.status === "tied")

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/"><Button variant="ghost" size="sm" className="text-slate-500 gap-1.5"><ArrowLeft className="h-4 w-4" />Dashboard</Button></Link>
            <div className="h-4 border-r border-slate-700" />
            <div className="flex items-center gap-2">
              <Swords className="h-5 w-5 text-amber-400" />
              <span className="font-bold text-lg">Week {data.week} Matchup</span>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => fetch_(true)} disabled={refreshing}>
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Matchup header card */}
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-center flex-1">
              <div className="text-lg font-bold text-emerald-400">{myName}</div>
              <div className="text-3xl font-black text-slate-100 mt-1">{summary.wins}</div>
              <div className="text-xs text-slate-500 mt-0.5">Wins</div>
            </div>
            <div className="text-center px-6">
              <div className="text-slate-600 text-sm">vs</div>
              {data.week_start && (
                <div className="text-xs text-slate-500 mt-1">{data.week_start} – {data.week_end}</div>
              )}
              {summary.close > 0 && (
                <div className="text-xs text-amber-400 mt-1 font-medium">{summary.close} swing cat{summary.close > 1 ? "s" : ""}</div>
              )}
            </div>
            <div className="text-center flex-1">
              <div className="text-lg font-bold text-slate-400">{oppName}</div>
              <div className="text-3xl font-black text-slate-100 mt-1">{summary.losses}</div>
              <div className="text-xs text-slate-500 mt-0.5">Opp wins</div>
            </div>
          </div>

          {isPre && (
            <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-4 py-3 text-center text-sm text-slate-400">
              Season starts {data.week_start ?? "soon"} — categories will populate when games are played.
            </div>
          )}
        </div>

        {/* Swing categories callout */}
        {summary.close > 0 && !isPre && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
            <div className="text-xs font-bold text-amber-400 uppercase tracking-wide mb-2">Focus here — swing categories</div>
            <div className="text-sm text-amber-200">
              {data.categories.filter(c => c.status === "close_win" || c.status === "close_loss")
                .map(c => c.label).join("  ·  ")}
            </div>
            <div className="text-xs text-amber-500/70 mt-1">
              These are within range — lineup and waiver decisions here matter most this week.
            </div>
          </div>
        )}

        {/* Batting */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
            <TrendingUp className="h-3.5 w-3.5" /> Batting
          </div>
          {batting.map(c => (
            <CategoryRow key={c.stat_id} cat={c} myName={myName} oppName={oppName} />
          ))}
        </section>

        {/* Pitching */}
        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
            <TrendingDown className="h-3.5 w-3.5" /> Pitching
          </div>
          {pitching.map(c => (
            <CategoryRow key={c.stat_id} cat={c} myName={myName} oppName={oppName} />
          ))}
        </section>

        <footer className="text-center text-xs text-slate-600 pb-4">
          Updated from Yahoo every 60s · Week {data.week}
        </footer>
      </div>
    </main>
  )
}

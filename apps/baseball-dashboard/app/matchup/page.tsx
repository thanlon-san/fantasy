"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { ArrowLeft, RefreshCw, TrendingUp, TrendingDown, AlertTriangle, Swords, Shield, Crosshair, Target, Lightbulb } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

import type { MatchupCategory, Matchup } from "@fantasy/types"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type CategoryStatus = "win" | "close_win" | "loss" | "close_loss" | "tied" | "unknown"

type EnhancedCategory = Omit<MatchupCategory, "status"> & { status: CategoryStatus }

type MatchupData = Omit<Matchup, "categories"> & {
  categories: EnhancedCategory[]
  days_elapsed: number
  days_left: number
  total_days: number
}

type ScoutingData = {
  opponent_name: string | null
  their_strengths: string[]
  their_weaknesses: string[]
  your_advantages: string[]
  threat_categories: string[]
  game_plan: string
  week: number
}

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

function scoreSummary(cats: EnhancedCategory[]): { wins: number; losses: number; close: number } {
  let wins = 0, losses = 0, close = 0
  for (const c of cats) {
    if (c.status === "win")        wins++
    else if (c.status === "loss")  losses++
    else if (c.status === "close_win" || c.status === "close_loss") close++
  }
  return { wins, losses, close }
}

function CategoryRow({ cat, myName, oppName }: { cat: EnhancedCategory; myName: string; oppName: string }) {
  const cfg     = statusConfig(cat.status)
  const isSwing = cat.status === "close_win" || cat.status === "close_loss"

  return (
    <div className={`border rounded-lg ${cfg.bg} ${cfg.border} ${isSwing ? "ring-1 ring-amber-500/20" : ""}`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />

        <div className="w-20 sm:w-24 shrink-0">
          <div className="font-bold text-sm text-slate-100">{cat.name}</div>
          <div className="text-[10px] text-slate-500 hidden sm:block">{cat.label}</div>
        </div>

        <div className="flex-1 text-right">
          <div className="text-sm font-mono font-semibold text-slate-100">{formatVal(cat.my_value, cat.name)}</div>
          <div className="text-[10px] text-slate-500 truncate hidden sm:block">{myName}</div>
        </div>

        <div className={`text-sm font-bold w-8 text-center ${cfg.text}`}>{cfg.icon}</div>

        <div className="flex-1 text-left">
          <div className="text-sm font-mono font-semibold text-slate-300">{formatVal(cat.opp_value, cat.name)}</div>
          <div className="text-[10px] text-slate-500 truncate hidden sm:block">{oppName}</div>
        </div>

        <div className={`text-[10px] font-bold w-16 text-right shrink-0 ${cfg.text}`}>
          {isSwing ? <span className="text-amber-400">⚠ SWING</span> : cfg.label}
        </div>
      </div>

      {/* Enhanced row: projections + gap + recommendation */}
      {isSwing && (cat.projected_my != null || cat.recommendation) && (
        <div className="border-t border-slate-700/40 px-4 py-2 bg-slate-900/40 space-y-1">
          <div className="flex items-center gap-4 text-[11px] flex-wrap">
            {cat.projected_my != null && cat.projected_opp != null && (
              <div className="flex items-center gap-1 text-slate-400">
                <Target className="h-3 w-3" />
                <span>Projected: <span className="text-slate-200 font-mono">{formatVal(cat.projected_my, cat.name)}</span> vs <span className="font-mono">{formatVal(cat.projected_opp, cat.name)}</span></span>
              </div>
            )}
            {cat.gap_to_flip != null && (
              <div className="flex items-center gap-1 text-slate-400">
                <span>Gap to flip: <span className={`font-mono font-semibold ${cat.status === "close_loss" ? "text-amber-300" : "text-emerald-300"}`}>{
                  cat.better === "high" ? cat.gap_to_flip.toFixed(cat.name === "OPS" ? 3 : 0) : cat.gap_to_flip.toFixed(3)
                }</span></span>
              </div>
            )}
          </div>
          {cat.recommendation && (
            <div className="flex items-start gap-1.5 text-[11px] text-amber-300/80">
              <Lightbulb className="h-3 w-3 mt-0.5 shrink-0 text-amber-400" />
              {cat.recommendation}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MatchupPage() {
  const [data,      setData]      = useState<MatchupData | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [refreshing,setRefreshing] = useState(false)
  const [scouting,  setScouting]  = useState<ScoutingData | null>(null)

  const fetch_ = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/season/matchup-enhanced`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      const raw = await res.json()
      setData(raw as MatchupData)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach server")
    } finally {
      setLoading(false)
      if (showRefresh) setRefreshing(false)
    }
  }, [])

  const fetchScouting = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/season/opponent`, { cache: "no-store" })
      if (!res.ok) return
      setScouting(await res.json())
    } catch {
      // silently ignore
    }
  }, [])

  useEffect(() => {
    fetch_()
    fetchScouting()
    const t = setInterval(() => { fetch_(); fetchScouting() }, 60_000)
    return () => clearInterval(t)
  }, [fetch_, fetchScouting])

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

  const swingCats = data.categories.filter(c => c.status === "close_win" || c.status === "close_loss")
  const actionableMoves = swingCats.filter(c => c.recommendation)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">

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
              {data.enhanced && data.days_left > 0 && (
                <div className="text-[10px] text-slate-500 mt-1">
                  Day {data.days_elapsed}/{data.total_days} · {data.days_left} left
                </div>
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

        {/* Actionable roster moves panel */}
        {actionableMoves.length > 0 && !isPre && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
            <div className="flex items-center gap-2 mb-1">
              <Lightbulb className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wide">Recommended Moves</span>
            </div>
            {actionableMoves.map(cat => (
              <div key={cat.stat_id} className="flex items-start gap-2 text-sm">
                <Badge variant="outline" className={`text-[10px] shrink-0 mt-0.5 ${cat.status === "close_loss" ? "border-amber-500/40 text-amber-300" : "border-emerald-500/40 text-emerald-300"}`}>
                  {cat.name}
                </Badge>
                <span className="text-slate-300">{cat.recommendation}</span>
              </div>
            ))}
          </div>
        )}

        {/* Swing categories callout */}
        {summary.close > 0 && !isPre && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
            <div className="text-xs font-bold text-amber-400 uppercase tracking-wide mb-2">Focus here — swing categories</div>
            <div className="text-sm text-amber-200">
              {swingCats.map(c => c.label).join("  ·  ")}
            </div>
            <div className="text-xs text-amber-500/70 mt-1">
              These are within range — lineup and waiver decisions here matter most this week.
            </div>
          </div>
        )}

        {/* Opponent Scouting Card */}
        {scouting && scouting.opponent_name && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Crosshair className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-bold text-slate-200">Opponent Scout: {scouting.opponent_name}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              {scouting.their_strengths.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                    <Shield className="h-3 w-3" /> Their Strengths
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {scouting.their_strengths.map(s => (
                      <Badge key={s} className="bg-red-500/20 text-red-400 border-red-500/30 text-[10px]">{s}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {scouting.their_weaknesses.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Their Weaknesses</div>
                  <div className="flex flex-wrap gap-1">
                    {scouting.their_weaknesses.map(s => (
                      <Badge key={s} className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[10px]">{s}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {scouting.your_advantages.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Your Advantages</div>
                  <div className="flex flex-wrap gap-1">
                    {scouting.your_advantages.map(s => (
                      <Badge key={s} className="bg-sky-500/20 text-sky-400 border-sky-500/30 text-[10px]">{s}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {scouting.threat_categories.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Threat Categories</div>
                  <div className="flex flex-wrap gap-1">
                    {scouting.threat_categories.map(s => (
                      <Badge key={s} className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-[10px]">{s}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {scouting.game_plan && (
              <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-4 py-3">
                <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Game Plan</div>
                <div className="text-sm text-slate-300 leading-relaxed">{scouting.game_plan}</div>
              </div>
            )}
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
          {data.enhanced && <span> · Enhanced analysis with projections</span>}
        </footer>
      </div>
    </main>
  )
}

"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { ArrowLeft, RefreshCw, Trophy, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type StatMeta = { name: string; label: string; group: string; better: string }
type Team = {
  team_key:   string
  name:       string
  is_mine:    boolean
  rank:       number
  wins:       number
  losses:     number
  ties:       number
  record:     string
  cat_ranks:  Record<string, number>
  cat_values: Record<string, number | null>
}
type StandingsData = {
  teams:          Team[]
  stat_map:       Record<string, StatMeta>
  season_started: boolean
}

const SCORING_ORDER = ["7","8","12","13","16","55","32","38","42","26","27","83"]
const BATTING_IDS   = new Set(["7","8","12","13","16","55"])

function rankColor(r: number, total: number): string {
  const pct = r / total
  if (pct <= 0.25) return "text-emerald-400 bg-emerald-500/10"
  if (pct <= 0.5)  return "text-sky-400 bg-sky-500/10"
  if (pct <= 0.75) return "text-amber-400 bg-amber-500/10"
  return "text-red-400 bg-red-500/10"
}

function formatVal(val: number | null | undefined, name: string): string {
  if (val === null || val === undefined) return "–"
  if (name === "ERA" || name === "WHIP" || name === "OPS") return val.toFixed(3)
  return val.toString()
}

export default function StandingsPage() {
  const [data,       setData]       = useState<StandingsData | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [view,       setView]       = useState<"ranks" | "values">("ranks")

  const fetch_ = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/season/standings`, { cache: "no-store" })
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
    const t = setInterval(() => fetch_(), 120_000)
    return () => clearInterval(t)
  }, [fetch_])

  if (loading) return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-500 animate-pulse text-sm">Loading standings…</div>
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

  const { teams, stat_map } = data
  const total = teams.length

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-screen-xl mx-auto px-4 py-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/"><Button variant="ghost" size="sm" className="text-slate-500 gap-1.5"><ArrowLeft className="h-4 w-4" />Dashboard</Button></Link>
            <div className="h-4 border-r border-slate-700" />
            <div className="flex items-center gap-2">
              <Trophy className="h-5 w-5 text-amber-400" />
              <span className="font-bold text-lg">Category Standings</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
              <button onClick={() => setView("ranks")} className={`px-3 py-1.5 ${view === "ranks" ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"}`}>Ranks</button>
              <button onClick={() => setView("values")} className={`px-3 py-1.5 ${view === "values" ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"}`}>Values</button>
            </div>
            <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => fetch_(true)} disabled={refreshing}>
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>

        {!data.season_started && (
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-3 text-center text-sm text-slate-400">
            Season starts March 25 — category stats will populate once games are played.
          </div>
        )}

        {/* Grid */}
        <div className="overflow-x-auto rounded-xl border border-slate-700/60">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/60 bg-slate-900/80">
                <th className="text-left px-4 py-3 font-semibold text-slate-400 w-8">Rank</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-400 w-40">Team</th>
                <th className="text-center px-2 py-3 font-semibold text-slate-400 w-20">Record</th>
                {/* Batting header */}
                <th className="px-1 py-1 text-center" colSpan={6}>
                  <span className="text-emerald-500/70 text-[10px] font-bold uppercase tracking-wider">Batting</span>
                </th>
                {/* Pitching header */}
                <th className="px-1 py-1 text-center" colSpan={6}>
                  <span className="text-blue-500/70 text-[10px] font-bold uppercase tracking-wider">Pitching</span>
                </th>
              </tr>
              <tr className="border-b border-slate-700/60 bg-slate-900/60">
                <th className="px-4 py-2" colSpan={3} />
                {SCORING_ORDER.map(sid => (
                  <th key={sid} className={`text-center px-2 py-2 font-bold w-14 ${BATTING_IDS.has(sid) ? "text-emerald-400/70" : "text-blue-400/70"}`}>
                    {stat_map[sid]?.name ?? sid}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {teams.map((team, i) => (
                <tr
                  key={team.team_key}
                  className={`border-b border-slate-800/60 transition-colors ${
                    team.is_mine
                      ? "bg-emerald-500/5 ring-inset ring-1 ring-emerald-500/20"
                      : i % 2 === 0 ? "bg-slate-900/20" : "bg-slate-900/40"
                  }`}
                >
                  <td className="px-4 py-2.5 text-slate-500 font-mono text-center">{team.rank}</td>
                  <td className="px-4 py-2.5">
                    <div className={`font-semibold ${team.is_mine ? "text-emerald-300" : "text-slate-200"} truncate max-w-[140px]`}>
                      {team.name}{team.is_mine && <span className="ml-1.5 text-[10px] text-emerald-500/70">you</span>}
                    </div>
                  </td>
                  <td className="px-2 py-2.5 text-center text-slate-400 font-mono">{team.record}</td>
                  {SCORING_ORDER.map(sid => {
                    const rank = team.cat_ranks[sid]
                    const val  = team.cat_values[sid]
                    const meta = stat_map[sid]
                    const cell = view === "ranks"
                      ? (rank ? rank.toString() : "–")
                      : formatVal(val ?? null, meta?.name ?? "")
                    const color = rank ? rankColor(rank, total) : "text-slate-600"
                    return (
                      <td key={sid} className="px-1 py-2.5 text-center">
                        <span className={`inline-block rounded px-1.5 py-0.5 font-mono font-semibold ${color}`}>
                          {cell}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-[10px] text-slate-500 px-1">
          <span className="font-medium text-slate-400">Rank color:</span>
          {[["1–3", "text-emerald-400"], ["4–6", "text-sky-400"], ["7–9", "text-amber-400"], ["10–12", "text-red-400"]].map(([label, cls]) => (
            <span key={label} className={`font-bold ${cls}`}>{label}</span>
          ))}
          <span className="ml-auto">Updated every 2min</span>
        </div>

      </div>
    </main>
  )
}

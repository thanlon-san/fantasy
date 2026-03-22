"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, RefreshCw, Zap, CheckCircle2, AlertTriangle, Wifi, WifiOff } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"
const POLL_MS  = 15_000

// ─── Types ────────────────────────────────────────────────────────────────────

type Recommendation = {
  rank:      number
  name:      string
  team:      string
  positions: string[]
  adp:       number
  tier:      string
  reason:    string
}

type RosterPlayer = {
  name:      string
  position:  string
  round:     number | null
  adp:       number | null
  is_keeper: boolean
}

type RecentPick = {
  overall:   number
  round:     number
  name:      string
  positions: string[]
  team:      string
  is_mine:   boolean
}

type NextPick = {
  round:      number
  overall:    number
  picks_away: number
}

type DraftState = {
  status:          "predraft" | "live" | "complete"
  picks_made:      number
  current_round:   number
  phase:           "BATTER_PRIORITY" | "SP_WINDOW" | "CLOSER_MODE"
  phase_label:     string
  my_next_pick:    NextPick | null
  recommendations: Recommendation[]
  my_roster:       RosterPlayer[]
  recent_picks:    RecentPick[]
  open_needs:      Record<string, number>
  last_synced:     string
  error:           string | null
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function positionBadgeClass(pos: string): string {
  if (["SP", "RP", "P"].includes(pos))  return "bg-blue-500/20 text-blue-300 border-blue-500/30"
  if (pos === "C")                       return "bg-amber-500/20 text-amber-300 border-amber-500/30"
  if (["SS", "2B", "3B"].includes(pos)) return "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
  if (pos === "1B")                      return "bg-green-500/20 text-green-300 border-green-500/30"
  if (pos === "OF")                      return "bg-purple-500/20 text-purple-300 border-purple-500/30"
  return "bg-slate-500/20 text-slate-300 border-slate-500/30"
}

function phaseConfig(phase: string) {
  if (phase === "BATTER_PRIORITY") return { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30", dot: "bg-emerald-400" }
  if (phase === "SP_WINDOW")       return { color: "text-amber-400",   bg: "bg-amber-500/10 border-amber-500/30",   dot: "bg-amber-400"   }
  return                                  { color: "text-purple-400",  bg: "bg-purple-500/10 border-purple-500/30", dot: "bg-purple-400"  }
}

function urgencyConfig(picksAway: number) {
  if (picksAway <= 1)  return { border: "border-emerald-400", bg: "bg-emerald-500/20", text: "text-emerald-300", pulse: true,  label: "YOUR PICK NOW" }
  if (picksAway <= 3)  return { border: "border-emerald-500", bg: "bg-emerald-500/10", text: "text-emerald-400", pulse: true,  label: `${picksAway} picks away` }
  if (picksAway <= 6)  return { border: "border-amber-500",   bg: "bg-amber-500/10",   text: "text-amber-400",  pulse: false, label: `${picksAway} picks away` }
  return                      { border: "border-slate-700",   bg: "bg-slate-800/50",   text: "text-slate-400",  pulse: false, label: `${picksAway} picks away` }
}

function tierColor(tier: string): string {
  if (tier === "Elite")  return "text-amber-400"
  if (tier === "Tier 1") return "text-emerald-400"
  if (tier === "Tier 2") return "text-sky-400"
  if (tier === "Tier 3") return "text-slate-300"
  return "text-slate-500"
}

// ─── Subcomponents ────────────────────────────────────────────────────────────

function StatusBar({ state, connected }: { state: DraftState; connected: boolean }) {
  const pc      = phaseConfig(state.phase)
  const picks   = state.my_next_pick
  const urgency = picks ? urgencyConfig(picks.picks_away) : null

  return (
    <div className="grid grid-cols-3 gap-3">
      {/* Round / Phase */}
      <div className={`rounded-xl border p-4 ${pc.bg}`}>
        <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
          Round {state.current_round} of 24
        </div>
        <div className={`text-sm font-bold ${pc.color}`}>{state.phase_label}</div>
        <div className="mt-2 text-xs text-slate-500">
          Pick {state.picks_made} / {12 * 24} made
        </div>
      </div>

      {/* Next pick countdown — center, biggest */}
      <div className={`rounded-xl border p-4 text-center ${urgency ? `${urgency.bg} ${urgency.border}` : "border-slate-700 bg-slate-800/50"} ${urgency?.pulse ? "animate-pulse" : ""}`}>
        <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Your next pick</div>
        {picks ? (
          <>
            <div className={`text-3xl font-black tracking-tight ${urgency?.text}`}>
              {picks.picks_away === 0 ? "NOW" : picks.picks_away}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {urgency?.label} · Round {picks.round} · #{picks.overall}
            </div>
          </>
        ) : (
          <div className="text-slate-500 text-sm">All picks done</div>
        )}
      </div>

      {/* Connection / sync */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-right">
        <div className="flex items-center justify-end gap-2 mb-1">
          {connected
            ? <Wifi className="h-3.5 w-3.5 text-emerald-400" />
            : <WifiOff className="h-3.5 w-3.5 text-red-400" />
          }
          <span className="text-xs text-slate-400">{connected ? "Connected" : "Offline"}</span>
        </div>
        <div className="text-xs text-slate-500">Synced {state.last_synced}</div>
        <div className="text-xs text-slate-600 mt-2">
          {Object.entries(state.open_needs)
            .filter(([, v]) => v > 0)
            .map(([k, v]) => `${k}×${v}`)
            .join("  ")}
        </div>
      </div>
    </div>
  )
}

function RecommendationRow({
  rec,
  onMine,
  onDrafted,
}: {
  rec: Recommendation
  onMine: (name: string) => void
  onDrafted: (name: string) => void
}) {
  const isPitcher = rec.positions.some(p => ["SP", "RP", "P"].includes(p))
  const isPenalized = rec.reason.includes("wait")

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 border-b border-slate-800/70 hover:bg-slate-800/40 transition-colors group ${isPenalized ? "opacity-40" : ""}`}>
      {/* Rank */}
      <span className="w-5 text-right text-xs font-mono text-slate-600 shrink-0">{rec.rank}</span>

      {/* ADP + tier */}
      <div className="w-14 text-right shrink-0">
        <div className="text-sm font-mono font-semibold text-slate-200">{Math.round(rec.adp)}</div>
        <div className={`text-[10px] ${tierColor(rec.tier)}`}>{rec.tier}</div>
      </div>

      {/* Position badges */}
      <div className="flex gap-1 shrink-0 w-28">
        {rec.positions.slice(0, 2).map(p => (
          <span key={p} className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${positionBadgeClass(p)}`}>
            {p}
          </span>
        ))}
      </div>

      {/* Name + team */}
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-slate-100 truncate">{rec.name}</div>
        <div className="text-[11px] text-slate-500">{rec.team} · <span className="text-slate-400">{rec.reason}</span></div>
      </div>

      {/* Actions — visible on hover */}
      <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2 text-xs text-emerald-400 hover:bg-emerald-500/20 hover:text-emerald-300"
          onClick={() => onMine(rec.name)}
        >
          Mine
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2 text-xs text-slate-500 hover:bg-slate-700 hover:text-slate-300"
          onClick={() => onDrafted(rec.name)}
        >
          Skip
        </Button>
      </div>
    </div>
  )
}

function RosterSlot({ player }: { player: RosterPlayer }) {
  const pc = positionBadgeClass(player.position)
  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-slate-800/50 last:border-0">
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${pc}`}>
        {player.position}
      </span>
      <span className="text-sm text-slate-200 flex-1 truncate">{player.name}</span>
      <span className="text-xs text-slate-600 shrink-0">
        {player.is_keeper ? <span className="text-amber-500/80">K</span> : `R${player.round}`}
      </span>
    </div>
  )
}

function PickLogRow({ pick }: { pick: RecentPick }) {
  const pos = pick.positions[0] ?? ""
  return (
    <div className={`flex items-center gap-2 py-1 text-xs border-b border-slate-800/40 last:border-0 ${pick.is_mine ? "bg-emerald-500/5" : ""}`}>
      <span className="font-mono text-slate-600 w-6 text-right shrink-0">{pick.overall}</span>
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${positionBadgeClass(pos)}`}>{pos}</span>
      <span className={`flex-1 truncate ${pick.is_mine ? "text-emerald-300 font-semibold" : "text-slate-300"}`}>{pick.name}</span>
      {pick.is_mine && <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function LiveDraftPage() {
  const [state,     setState]     = useState<DraftState | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [connected, setConnected] = useState(false)
  const [refreshing,setRefreshing] = useState(false)
  const [apiError,  setApiError]  = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchState = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/state`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data: DraftState = await res.json()
      setState(data)
      setConnected(true)
      setApiError(null)
    } catch (e) {
      setConnected(false)
      setApiError(e instanceof Error ? e.message : "Cannot reach draft server")
    } finally {
      setLoading(false)
      if (showRefreshing) setRefreshing(false)
    }
  }, [])

  const markPick = useCallback(async (playerName: string, isMine: boolean) => {
    try {
      await fetch(`${API_BASE}/mark-pick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_name: playerName, is_mine: isMine }),
      })
      await fetchState()
    } catch {/* silent */}
  }, [fetchState])

  useEffect(() => {
    fetchState()
    timerRef.current = setInterval(() => fetchState(), POLL_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [fetchState])

  // ── Loading / Error screens ──────────────────────────────────────────────

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-4xl">⚾</div>
          <div className="text-slate-400 text-sm animate-pulse">Connecting to draft server…</div>
          <div className="text-slate-600 text-xs">{API_BASE}</div>
        </div>
      </main>
    )
  }

  if (!connected || !state) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-sm">
          <WifiOff className="h-12 w-12 text-slate-600 mx-auto" />
          <div className="text-slate-300 font-semibold">Draft server not reachable</div>
          <div className="text-slate-500 text-sm">{apiError}</div>
          <div className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-left text-xs font-mono text-slate-400 space-y-1">
            <div className="text-slate-300 font-semibold mb-2">Start the server:</div>
            <div>cd apps/keeper-advisor</div>
            <div>python scripts/draft_server.py</div>
          </div>
          <Button variant="outline" size="sm" onClick={() => fetchState(true)}>
            Retry
          </Button>
        </div>
      </main>
    )
  }

  // ── Pre-draft state ──────────────────────────────────────────────────────

  if (state.status === "predraft") {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-5xl">⏳</div>
          <div className="text-slate-200 text-xl font-bold">Draft hasn't started yet</div>
          <div className="text-slate-400 text-sm">This page will update automatically when picks begin.</div>
          <div className="text-slate-600 text-xs">Polling every {POLL_MS / 1000}s · {state.last_synced}</div>
          <Button variant="ghost" size="sm" onClick={() => fetchState(true)} disabled={refreshing}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? "animate-spin" : ""}`} />
            Check now
          </Button>
        </div>
      </main>
    )
  }

  const picks_away = state.my_next_pick?.picks_away ?? 999
  const isPickSoon = picks_away <= 3

  // ── Live draft UI ────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-screen-xl mx-auto px-4 py-5 space-y-4">

        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/draft">
              <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-300 gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                Draft Board
              </Button>
            </Link>
            <div className="h-4 border-r border-slate-700" />
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-400" />
              <span className="font-bold text-lg tracking-tight">Live Draft</span>
              <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-500">
                2balls · Pick 11/12
              </Badge>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-slate-500 hover:text-slate-300"
            onClick={() => fetchState(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </header>

        {/* Your pick alert banner */}
        {isPickSoon && (
          <div className={`rounded-xl border-2 border-emerald-400 bg-emerald-500/10 px-5 py-3 flex items-center justify-between animate-pulse`}>
            <div className="font-black text-emerald-300 text-lg tracking-wide">
              {picks_away === 0 ? "⚡ YOUR PICK — DRAFT NOW" : `⚡ ${picks_away} PICK${picks_away > 1 ? "S" : ""} UNTIL YOURS`}
            </div>
            <div className="text-sm text-emerald-400">
              Round {state.my_next_pick?.round} · Overall #{state.my_next_pick?.overall}
            </div>
          </div>
        )}

        {/* Status bar */}
        <StatusBar state={state} connected={connected} />

        {/* Main content — 3 columns */}
        <div className="grid grid-cols-12 gap-4">

          {/* Recommendations — left 7 cols */}
          <div className="col-span-12 lg:col-span-7 rounded-xl border border-slate-700/60 bg-slate-900/60 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-700/60 flex items-center justify-between">
              <div className="font-semibold text-sm">Recommendations</div>
              <div className={`text-xs px-2 py-0.5 rounded-full border ${phaseConfig(state.phase).bg} ${phaseConfig(state.phase).color}`}>
                {state.phase.replace("_", " ")}
              </div>
            </div>
            <div className="divide-y-0">
              {state.recommendations.map(rec => (
                <RecommendationRow
                  key={rec.name}
                  rec={rec}
                  onMine={(name) => markPick(name, true)}
                  onDrafted={(name) => markPick(name, false)}
                />
              ))}
              {state.recommendations.length === 0 && (
                <div className="px-4 py-8 text-center text-slate-500 text-sm">
                  No recommendations — all positions may be filled.
                </div>
              )}
            </div>
          </div>

          {/* Right panel — 5 cols */}
          <div className="col-span-12 lg:col-span-5 flex flex-col gap-4">

            {/* My Roster */}
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700/60 flex items-center justify-between">
                <div className="font-semibold text-sm">My Roster</div>
                <span className="text-xs text-slate-500">
                  {state.my_roster.length} / 24
                </span>
              </div>
              <div className="px-4 py-2">
                {state.my_roster.length === 0 ? (
                  <div className="py-4 text-center text-slate-600 text-sm">No picks yet</div>
                ) : (
                  state.my_roster.map((p, i) => (
                    <RosterSlot key={i} player={p} />
                  ))
                )}
              </div>
            </div>

            {/* Recent picks log */}
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 overflow-hidden flex-1">
              <div className="px-4 py-3 border-b border-slate-700/60 flex items-center justify-between">
                <div className="font-semibold text-sm">Pick Log</div>
                <span className="text-xs text-slate-500">Most recent first</span>
              </div>
              <div className="px-4 py-2 max-h-72 overflow-y-auto">
                {state.recent_picks.length === 0 ? (
                  <div className="py-4 text-center text-slate-600 text-sm">Waiting for picks…</div>
                ) : (
                  state.recent_picks.map((pick, i) => (
                    <PickLogRow key={i} pick={pick} />
                  ))
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Error notice */}
        {state.error && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-700/50 bg-amber-900/20 px-4 py-2.5 text-sm text-amber-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {state.error}
          </div>
        )}

      </div>
    </main>
  )
}

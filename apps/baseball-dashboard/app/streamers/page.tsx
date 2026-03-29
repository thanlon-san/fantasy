"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { ArrowLeft, RefreshCw, Radio, CalendarDays, Flame } from "lucide-react"

import type { BullpenAlert } from "@fantasy/types"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type ScheduledStart = {
  date: string
  opponent: string
  home_away: string
  opp_k_pct: number
  park_factor: number
}

type Streamer = {
  pitcher: string
  team: string
  starts: ScheduledStart[]
  composite_score: number
  pitcher_fip: number | null
  reason: string
}

type CloserFatigue = {
  name: string
  team: string
  fatigue_score: number
  fatigue_level: string
  consecutive_days: number
  pitches_last_3_days: number
  innings_last_7_days: number
  appearances_last_7_days: number
  last_outing_date: string | null
}

type StreamerData = {
  streamers: Streamer[]
  week_dates: { start: string; end: string }
  generated_at: string
}

type BullpenData = {
  alerts: BullpenAlert[]
  closer_fatigue: CloserFatigue[]
  generated_at: string
}

function scoreBadge(score: number) {
  if (score >= 70) return "bg-emerald-600 text-white"
  if (score >= 45) return "bg-amber-600 text-white"
  return "bg-slate-600 text-white"
}

function kPctColor(k: number) {
  if (k >= 24) return "text-emerald-400 font-semibold"
  if (k >= 22) return "text-slate-300"
  return "text-red-400"
}

function fatigueBadge(level: string) {
  if (level === "HIGH") return "bg-red-500/20 text-red-300 border-red-500/40"
  if (level === "MODERATE") return "bg-amber-500/20 text-amber-300 border-amber-500/40"
  if (level === "LOW") return "bg-sky-500/20 text-sky-300 border-sky-500/40"
  return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
}

export default function StreamersPage() {
  const { data: streamers, isLoading: sLoading } = useQuery<StreamerData>({
    queryKey: ["streamers"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/streamers`, { cache: "no-store" })
      if (!res.ok) throw new Error(`Streamers API ${res.status}`)
      return res.json()
    },
  })

  const { data: bullpen, isLoading: bLoading } = useQuery<BullpenData>({
    queryKey: ["bullpen-alerts"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/bullpen-alerts`, { cache: "no-store" })
      if (!res.ok) throw new Error(`Bullpen API ${res.status}`)
      return res.json()
    },
  })

  const loading = sLoading || bLoading
  const error = !streamers && !sLoading ? "Failed to load streamer data" : null

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />Dashboard</Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Radio className="h-6 w-6 text-primary" />
              Streamers &amp; Bullpen
            </h1>
          </div>
          <Button variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            {error}. Make sure the season server is running on port 8001.
          </div>
        )}

        <section className="mb-8">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Flame className="h-5 w-5 text-red-400" />
            Vulture Save Alerts
          </h2>

          {bullpen && bullpen.alerts.length > 0 ? (
            <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-200 dark:border-slate-700/60">
                    <TableHead className="w-[140px]">Closer</TableHead>
                    <TableHead className="w-[60px]">Team</TableHead>
                    <TableHead className="w-[90px]">Fatigue</TableHead>
                    <TableHead className="w-[80px]">Consec. Days</TableHead>
                    <TableHead className="w-[80px]">Pitches 3d</TableHead>
                    <TableHead className="w-[160px]">Vulture Add</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bullpen.alerts.map(a => (
                    <TableRow key={a.closer} className="border-slate-200 dark:border-slate-700/40">
                      <TableCell className="font-semibold">{a.closer}</TableCell>
                      <TableCell className="text-muted-foreground">{a.closer_team}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`text-[10px] ${fatigueBadge(a.fatigue_level)}`}>
                          {a.fatigue_level} ({a.fatigue_score})
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">{a.consecutive_days}</TableCell>
                      <TableCell className="text-center">{a.pitches_last_3_days}</TableCell>
                      <TableCell className="font-semibold text-emerald-500">{a.vulture_candidate}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center border rounded-lg border-dashed">
              {loading ? "Loading bullpen data..." : "No fatigued closers right now — no vulture opportunities."}
            </p>
          )}

          {bullpen && bullpen.closer_fatigue && bullpen.closer_fatigue.length > 0 && (
            <details className="mt-4">
              <summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground">
                View all closer fatigue ({bullpen.closer_fatigue.length} closers)
              </summary>
              <div className="mt-2 rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-200 dark:border-slate-700/60">
                      <TableHead>Closer</TableHead>
                      <TableHead className="w-[50px]">Team</TableHead>
                      <TableHead className="w-[80px]">Level</TableHead>
                      <TableHead className="w-[60px] text-center">Score</TableHead>
                      <TableHead className="w-[50px] text-center">Days</TableHead>
                      <TableHead className="w-[60px] text-center">P (3d)</TableHead>
                      <TableHead className="w-[60px] text-center">IP (7d)</TableHead>
                      <TableHead className="w-[50px] text-center">App</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {bullpen.closer_fatigue
                      .slice()
                      .sort((a, b) => b.fatigue_score - a.fatigue_score)
                      .map(f => (
                        <TableRow key={f.name} className="border-slate-200 dark:border-slate-700/40">
                          <TableCell className="font-medium">{f.name}</TableCell>
                          <TableCell className="text-muted-foreground">{f.team}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={`text-[10px] ${fatigueBadge(f.fatigue_level)}`}>
                              {f.fatigue_level}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-center">{f.fatigue_score}</TableCell>
                          <TableCell className="text-center">{f.consecutive_days}</TableCell>
                          <TableCell className="text-center">{f.pitches_last_3_days}</TableCell>
                          <TableCell className="text-center">{f.innings_last_7_days}</TableCell>
                          <TableCell className="text-center">{f.appearances_last_7_days}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </div>
            </details>
          )}
        </section>

        <section className="mb-8">
          <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-primary" />
            Two-Start Pitcher Streamers
          </h2>
          {streamers?.week_dates && (
            <p className="text-sm text-muted-foreground mb-3">
              Week of {streamers.week_dates.start} — {streamers.week_dates.end}
            </p>
          )}

          {streamers && streamers.streamers.length > 0 ? (
            <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-200 dark:border-slate-700/60">
                    <TableHead className="w-[180px]">Pitcher</TableHead>
                    <TableHead className="w-[50px]">Team</TableHead>
                    <TableHead className="w-[80px]">Score</TableHead>
                    <TableHead className="w-[70px]">FIP</TableHead>
                    <TableHead>Start 1</TableHead>
                    <TableHead>Start 2</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {streamers.streamers.map(s => (
                    <TableRow key={s.pitcher} className="border-slate-200 dark:border-slate-700/40">
                      <TableCell className="font-semibold">{s.pitcher}</TableCell>
                      <TableCell className="text-muted-foreground">{s.team}</TableCell>
                      <TableCell>
                        <Badge className={`text-xs ${scoreBadge(s.composite_score)}`}>
                          {s.composite_score}
                        </Badge>
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {s.pitcher_fip != null ? s.pitcher_fip.toFixed(2) : "—"}
                      </TableCell>
                      {s.starts.slice(0, 2).map((st, i) => (
                        <TableCell key={i}>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs text-muted-foreground">{st.date.slice(5)}</span>
                            <span className={`font-medium ${st.home_away === "home" ? "text-emerald-400" : ""}`}>
                              {st.home_away === "home" ? "vs" : "@"} {st.opponent}
                            </span>
                            <span className={`text-xs ${kPctColor(st.opp_k_pct)}`}>
                              {st.opp_k_pct}% K
                            </span>
                          </div>
                        </TableCell>
                      ))}
                      {s.starts.length < 2 && <TableCell />}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center border rounded-lg border-dashed">
              {loading ? "Loading streamer data..." : "No two-start pitchers found for next week yet."}
            </p>
          )}
        </section>

        <footer className="text-center text-sm text-muted-foreground mt-8">
          <p>Bullpen fatigue + two-start streamers refresh every 2 minutes.</p>
          <p className="mt-1">Best viewed Thu–Sat for planning next week&apos;s pickups.</p>
        </footer>
      </div>
    </main>
  )
}

"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, RefreshCw, CalendarRange, Zap, Users } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type DailyStream = {
  date: string
  pitcher: string
  team: string
  opponent: string
  home_away: string
  opp_k_pct: number
  opp_wrc_plus: number
  park_factor: number
  game_total: number | null
  score: number
  reason: string
}

type TeamGameCount = {
  team: string
  games: number
  opponents: string[]
}

type PlanData = {
  week_start: string
  week_end: string
  daily_streams: Record<string, DailyStream[]>
  optimal_streams: DailyStream[]
  team_game_counts: TeamGameCount[]
  generated_at: string
}

function scoreBadge(score: number) {
  if (score >= 65) return "bg-emerald-600 text-white"
  if (score >= 45) return "bg-amber-600 text-white"
  return "bg-slate-600 text-white"
}

function kColor(k: number) {
  if (k >= 24) return "text-emerald-400 font-semibold"
  if (k >= 22) return "text-slate-300"
  return "text-red-400"
}

function dayLabel(dateStr: string) {
  try {
    const d = new Date(dateStr + "T12:00:00")
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })
  } catch {
    return dateStr
  }
}

export default function PlannerPage() {
  const { data, isLoading, error, refetch } = useQuery<PlanData>({
    queryKey: ["weekly-plan"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/weekly-plan`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      return res.json()
    },
  })

  const dates = data ? Object.keys(data.daily_streams).sort() : []

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />Dashboard</Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <CalendarRange className="h-6 w-6 text-primary" />
              Weekly Planner
            </h1>
            {data && (
              <span className="text-sm text-muted-foreground ml-2">
                {data.week_start} — {data.week_end}
              </span>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            {error instanceof Error ? error.message : "Failed to load"}. Make sure the season server is running on port 8001.
          </div>
        )}

        <Tabs defaultValue="optimal" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="optimal" className="gap-1.5"><Zap className="h-3.5 w-3.5" />Optimal Plan</TabsTrigger>
            <TabsTrigger value="daily" className="gap-1.5"><CalendarRange className="h-3.5 w-3.5" />Day-by-Day</TabsTrigger>
            <TabsTrigger value="games" className="gap-1.5"><Users className="h-3.5 w-3.5" />Team Games</TabsTrigger>
          </TabsList>

          <TabsContent value="optimal">
            <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-400" />
              Best Stream Per Day
            </h2>
            {data && data.optimal_streams.length > 0 ? (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-200 dark:border-slate-700/60">
                      <TableHead className="w-[140px]">Day</TableHead>
                      <TableHead className="w-[160px]">Pitcher</TableHead>
                      <TableHead className="w-[50px]">Team</TableHead>
                      <TableHead>Matchup</TableHead>
                      <TableHead className="w-[70px]">Score</TableHead>
                      <TableHead>Why</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.optimal_streams.map(s => (
                      <TableRow key={s.date} className="border-slate-200 dark:border-slate-700/40">
                        <TableCell className="font-medium">{dayLabel(s.date)}</TableCell>
                        <TableCell className="font-semibold">{s.pitcher}</TableCell>
                        <TableCell className="text-muted-foreground">{s.team}</TableCell>
                        <TableCell>
                          <span className={s.home_away === "home" ? "text-emerald-400" : ""}>
                            {s.home_away === "home" ? "vs" : "@"} {s.opponent}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={`text-xs ${scoreBadge(s.score)}`}>{s.score}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{s.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                {isLoading ? "Loading weekly plan..." : "No schedule data available for next week."}
              </p>
            )}
          </TabsContent>

          <TabsContent value="daily">
            {dates.length > 0 ? (
              <div className="space-y-6">
                {dates.map(date => {
                  const streams = data?.daily_streams[date] || []
                  return (
                    <div key={date}>
                      <h3 className="text-sm font-bold mb-2 text-muted-foreground uppercase tracking-wider">
                        {dayLabel(date)}
                        <span className="ml-2 text-slate-500 font-normal">({streams.length} options)</span>
                      </h3>
                      <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="border-slate-200 dark:border-slate-700/60">
                              <TableHead className="w-[160px]">Pitcher</TableHead>
                              <TableHead className="w-[50px]">Team</TableHead>
                              <TableHead>Matchup</TableHead>
                              <TableHead className="w-[65px]">K%</TableHead>
                              <TableHead className="w-[65px]">wRC+</TableHead>
                              <TableHead className="w-[55px]">PF</TableHead>
                              <TableHead className="w-[55px]">Total</TableHead>
                              <TableHead className="w-[60px]">Score</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {streams.map((s, i) => (
                              <TableRow key={`${s.pitcher}-${i}`} className={`border-slate-200 dark:border-slate-700/40 ${i === 0 ? "bg-emerald-500/5" : ""}`}>
                                <TableCell className={`font-medium ${i === 0 ? "font-semibold" : ""}`}>
                                  {s.pitcher}
                                </TableCell>
                                <TableCell className="text-muted-foreground">{s.team}</TableCell>
                                <TableCell>
                                  <span className={s.home_away === "home" ? "text-emerald-400" : ""}>
                                    {s.home_away === "home" ? "vs" : "@"} {s.opponent}
                                  </span>
                                </TableCell>
                                <TableCell className={kColor(s.opp_k_pct)}>{s.opp_k_pct}%</TableCell>
                                <TableCell className={s.opp_wrc_plus <= 90 ? "text-emerald-400" : s.opp_wrc_plus >= 105 ? "text-red-400" : ""}>
                                  {s.opp_wrc_plus}
                                </TableCell>
                                <TableCell className={s.park_factor <= 0.95 ? "text-emerald-400" : s.park_factor >= 1.05 ? "text-red-400" : ""}>
                                  {s.park_factor.toFixed(2)}
                                </TableCell>
                                <TableCell className="tabular-nums">
                                  {s.game_total != null ? s.game_total.toFixed(1) : "—"}
                                </TableCell>
                                <TableCell>
                                  <Badge className={`text-xs ${scoreBadge(s.score)}`}>{s.score}</Badge>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                {isLoading ? "Loading daily streams..." : "No schedule data available."}
              </p>
            )}
          </TabsContent>

          <TabsContent value="games">
            <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Team Game Counts — Next Week
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Teams with more games produce more counting stats (R, H, HR, RBI, SB, K). Prioritize hitters on 7-game teams over 5-game teams.
            </p>
            {data && data.team_game_counts.length > 0 ? (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-200 dark:border-slate-700/60">
                      <TableHead className="w-[60px]">Team</TableHead>
                      <TableHead className="w-[70px]">Games</TableHead>
                      <TableHead>Opponents</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.team_game_counts.map(c => (
                      <TableRow key={c.team} className="border-slate-200 dark:border-slate-700/40">
                        <TableCell className="font-semibold">{c.team}</TableCell>
                        <TableCell>
                          <Badge className={`text-xs ${
                            c.games >= 7 ? "bg-emerald-600 text-white" :
                            c.games >= 6 ? "bg-amber-600 text-white" :
                            "bg-slate-600 text-white"
                          }`}>
                            {c.games}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {c.opponents.join(", ")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                {isLoading ? "Loading game counts..." : "No schedule data available."}
              </p>
            )}
          </TabsContent>
        </Tabs>

        <footer className="text-center text-sm text-muted-foreground mt-10">
          <p>Weekly plan refreshes every 2 minutes. Scores combine opponent K%, wRC+, park factor, and Vegas totals.</p>
          <p className="mt-1">Best viewed Thu–Sat for planning next week&apos;s moves.</p>
        </footer>
      </div>
    </main>
  )
}

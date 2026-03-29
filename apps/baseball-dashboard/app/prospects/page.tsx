"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, RefreshCw, Sparkles, Flame, Users, Star } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type Prospect = {
  name: string
  mlb_id: number
  team: string
  position: string
  level: string
  top_100_rank: number
  eta: string
  games_14d: number
  ab_14d: number
  hits_14d: number
  hr_14d: number
  rbi_14d: number
  sb_14d: number
  avg_14d: number
  ops_14d: number
  k_14d: number
  bb_14d: number
  ip_14d: number
  p_k_14d: number
  p_bb_14d: number
  era_14d: number
  whip_14d: number
  p_games_14d: number
  is_pitcher: boolean
  is_hot: boolean
  hot_streak_ops: number
  is_on_40_man: boolean
  roster_status: string
  callup_score: number
  alert_reasons: string[]
}

type ProspectsData = {
  prospects: Prospect[]
  hot_prospects: Prospect[]
  total: number
  hot_count: number
  generated_at: string
}

function scoreBadge(score: number) {
  if (score >= 70) return "bg-emerald-600 text-white"
  if (score >= 45) return "bg-amber-600 text-white"
  if (score >= 25) return "bg-sky-600 text-white"
  return "bg-slate-600 text-white"
}

function levelBadge(level: string) {
  switch (level) {
    case "MLB": return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
    case "AAA": return "bg-sky-500/20 text-sky-300 border-sky-500/40"
    case "AA":  return "bg-amber-500/20 text-amber-300 border-amber-500/40"
    case "A+":  return "bg-violet-500/20 text-violet-300 border-violet-500/40"
    default:    return "bg-slate-500/20 text-slate-300 border-slate-500/40"
  }
}

function HotProspectCard({ p }: { p: Prospect }) {
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-amber-400" />
            <span className="font-bold text-sm">{p.name}</span>
            <Badge variant="outline" className={`text-[10px] ${levelBadge(p.level)}`}>{p.level}</Badge>
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {p.position} · {p.team} · #{p.top_100_rank} prospect
          </div>
        </div>
        <Badge className={`text-xs ${scoreBadge(p.callup_score)}`}>{p.callup_score}</Badge>
      </div>
      {!p.is_pitcher ? (
        <div className="grid grid-cols-4 gap-2 text-xs mt-3">
          <div className="text-center">
            <div className="text-muted-foreground">AVG</div>
            <div className="font-mono font-semibold">{p.avg_14d.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">OPS</div>
            <div className={`font-mono font-semibold ${p.ops_14d >= 1.0 ? "text-emerald-400" : ""}`}>{p.ops_14d.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">HR</div>
            <div className="font-mono font-semibold">{p.hr_14d}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">SB</div>
            <div className="font-mono font-semibold">{p.sb_14d}</div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-2 text-xs mt-3">
          <div className="text-center">
            <div className="text-muted-foreground">ERA</div>
            <div className={`font-mono font-semibold ${p.era_14d <= 2.5 ? "text-emerald-400" : ""}`}>{p.era_14d.toFixed(2)}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">WHIP</div>
            <div className="font-mono font-semibold">{p.whip_14d.toFixed(2)}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">K</div>
            <div className="font-mono font-semibold">{p.p_k_14d}</div>
          </div>
          <div className="text-center">
            <div className="text-muted-foreground">IP</div>
            <div className="font-mono font-semibold">{p.ip_14d.toFixed(1)}</div>
          </div>
        </div>
      )}
      {p.alert_reasons.length > 0 && (
        <div className="mt-3 space-y-1">
          {p.alert_reasons.map((reason, i) => (
            <div key={i} className="text-xs text-amber-300/80 flex items-start gap-1.5">
              <Sparkles className="h-3 w-3 mt-0.5 shrink-0" />
              {reason}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ProspectsPage() {
  const { data, isLoading, error, refetch } = useQuery<ProspectsData>({
    queryKey: ["prospects"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/prospects`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      return res.json()
    },
  })

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />Dashboard</Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Star className="h-6 w-6 text-amber-400" />
              Prospect Watch
            </h1>
            {data && (
              <Badge variant="secondary" className="text-xs">
                {data.hot_count} hot
              </Badge>
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

        <Tabs defaultValue="hot" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="hot" className="gap-1.5"><Flame className="h-3.5 w-3.5" />Hot Prospects</TabsTrigger>
            <TabsTrigger value="all" className="gap-1.5"><Users className="h-3.5 w-3.5" />Full Watchlist</TabsTrigger>
          </TabsList>

          <TabsContent value="hot">
            {data && data.hot_prospects.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {data.hot_prospects.map(p => (
                  <HotProspectCard key={p.mlb_id} p={p} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                {isLoading ? "Scanning prospect game logs..." : "No hot prospects right now — check back during the season."}
              </p>
            )}
          </TabsContent>

          <TabsContent value="all">
            {data && data.prospects.length > 0 ? (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-200 dark:border-slate-700/60">
                      <TableHead className="w-[40px]">#</TableHead>
                      <TableHead className="w-[160px]">Player</TableHead>
                      <TableHead className="w-[50px]">Pos</TableHead>
                      <TableHead className="w-[50px]">Team</TableHead>
                      <TableHead className="w-[60px]">Level</TableHead>
                      <TableHead className="w-[50px]">ETA</TableHead>
                      <TableHead className="w-[50px] text-center">G</TableHead>
                      <TableHead className="w-[60px] text-right">AVG/ERA</TableHead>
                      <TableHead className="w-[65px] text-right">OPS/WHIP</TableHead>
                      <TableHead className="w-[45px] text-center">HR/K</TableHead>
                      <TableHead className="w-[55px]">40-Man</TableHead>
                      <TableHead className="w-[60px]">Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.prospects.map(p => (
                      <TableRow key={p.mlb_id} className={`border-slate-200 dark:border-slate-700/40 ${p.is_hot ? "bg-amber-500/5" : ""}`}>
                        <TableCell className="text-muted-foreground text-xs">{p.top_100_rank}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-sm">{p.name}</span>
                            {p.is_hot && <Flame className="h-3 w-3 text-amber-400" />}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{p.position}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{p.team}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-[10px] ${levelBadge(p.level)}`}>{p.level}</Badge>
                        </TableCell>
                        <TableCell className="text-xs">{p.eta}</TableCell>
                        <TableCell className="text-center text-xs tabular-nums">
                          {p.is_pitcher ? p.p_games_14d : p.games_14d}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">
                          {p.is_pitcher
                            ? (p.ip_14d > 0 ? p.era_14d.toFixed(2) : "—")
                            : (p.ab_14d > 0 ? p.avg_14d.toFixed(3) : "—")}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">
                          {p.is_pitcher
                            ? (p.ip_14d > 0 ? p.whip_14d.toFixed(2) : "—")
                            : (p.ab_14d > 0 ? p.ops_14d.toFixed(3) : "—")}
                        </TableCell>
                        <TableCell className="text-center text-xs tabular-nums">
                          {p.is_pitcher ? p.p_k_14d : p.hr_14d}
                        </TableCell>
                        <TableCell>
                          {p.is_on_40_man ? (
                            <Badge variant="outline" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/40">Yes</Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">No</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge className={`text-xs ${scoreBadge(p.callup_score)}`}>{p.callup_score}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                {isLoading ? "Loading prospect data..." : "No prospects in watchlist."}
              </p>
            )}
          </TabsContent>
        </Tabs>

        <footer className="text-center text-sm text-muted-foreground mt-8">
          <p>Prospect data from MLB Stats API minor league game logs. Updates hourly.</p>
          <p className="mt-1">Top 50 prospects curated for fantasy relevance. Edit data/prospect_watchlist.json to customize.</p>
        </footer>
      </div>
    </main>
  )
}

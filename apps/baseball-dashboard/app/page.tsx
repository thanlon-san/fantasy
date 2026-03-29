"use client"

import { useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, Users, Calendar, Copy, AlertCircle, Star, Swords, Trophy, Shield, Zap, TrendingUp } from "lucide-react"
import { useState, useEffect, useMemo } from "react"
import Link from "next/link"
import { PlayerTable } from "@/components/player-table"
import { OptimalLineupView } from "@/components/optimal-lineup"
import { NotPlayingTable } from "@/components/not-playing-table"
import { DashboardSkeleton } from "@/components/loading-skeleton"
import { CommandPalette } from "@/components/command-palette"
import { FilterBar } from "@/components/filter-bar"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import { KeeperAnalyzerTable } from "@/components/keeper-analyzer-table"
import { useToast } from "@/components/ui/use-toast"
import { ThemeToggle } from "@/components/theme-toggle"
import { WaiverWireTable } from "@/components/waiver-wire-table"
import { BreakoutDetectorTable } from "@/components/breakout-detector-table"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const DRAFT_API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"
const BASE_PATH = process.env.NODE_ENV === 'production' ? '/fantasy/baseball' : ''
const USE_API = process.env.NEXT_PUBLIC_USE_API === 'true'

type Player = {
  player: string
  position: string
  team: string
  opponent: string
  opponent_pitcher?: string
  game_time?: string
  confidence: number
  matchup: number
  parkFactor: number
  platoon: number
  form: number
  breakout: number
  reasons: string[]
}

type WaiverTarget = {
  player: string
  position: string
  team: string
  confidence: string
  reason: string
  drop_player: string
  drop_player_position: string
  adp?: number
  value_gain?: number
  drop_player_adp?: number
  keeper_cost?: number
  rostered_pct?: number
  trending?: "HOT" | "COLD" | "STABLE"
  last_7_days?: {
    avg?: number; hr?: number; rbi?: number; sb?: number
    era?: number; whip?: number; k?: number; w?: number; games?: number
  }
  last_14_days?: {
    avg?: number; hr?: number; rbi?: number; sb?: number
    era?: number; whip?: number; k?: number; w?: number; games?: number
  }
  last_30_days?: {
    avg?: number; hr?: number; rbi?: number; sb?: number
    era?: number; whip?: number; k?: number; w?: number; games?: number
  }
  statcast_changes?: {
    exit_velo?: string; hard_hit_pct?: string; barrel_rate?: string
    velo?: string; chase_rate?: string; whiff_rate?: string
  }
  role_change?: string
  upcoming_schedule?: string
}

type Breakout = {
  player: string
  position: string
  team: string
  signal: string
  stats: string[]
  category: string
  confidence: number
}

type Keeper = {
  player: string
  position?: string
  round: number | string
  adp: number
  surplus: string
  value: string
  years_remaining?: number
  reason?: string
}

type SwingCategory = {
  stat_name: string
  stat_id: string
  status: "close_win" | "close_loss"
  my_value: number | null
  opp_value: number | null
  focus_players: string[]
  waiver_suggestion: string | null
}

type LineupFocus = {
  week: number
  swing_categories: SwingCategory[]
  season_started: boolean
}

export default function Home() {
  const { toast } = useToast()

  const [searchTerm, setSearchTerm] = useState("")
  const [positionFilter, setPositionFilter] = useState("all")
  const [confidenceThreshold, setConfidenceThreshold] = useState(0)

  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)

  const [dailyLineup, setDailyLineup] = useState<{
    must_start: Player[]
    start: Player[]
    flex: Player[]
    bench: Player[]
    not_playing: { player: string; position: string; team: string; adp?: number }[]
    summary?: { total_roster: number; playing_today: number; not_playing: number }
  }>({ must_start: [], start: [], flex: [], bench: [], not_playing: [] })

  const [waiverWire, setWaiverWire] = useState<WaiverTarget[]>([])
  const [breakouts, setBreakouts] = useState<Breakout[]>([])
  const [keepers, setKeepers] = useState<Keeper[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dataTimestamp, setDataTimestamp] = useState<string | null>(null)
  const [lineupFocus, setLineupFocus] = useState<LineupFocus | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        let lineupData, waiverData, breakoutData, keeperData

        if (USE_API) {
          const [lineupRes, waiverRes, breakoutRes, keeperRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/lineup`),
            fetch(`${API_BASE_URL}/api/waivers`),
            fetch(`${API_BASE_URL}/api/breakouts`),
            fetch(`${API_BASE_URL}/api/keepers`),
          ])
          ;[lineupData, waiverData, breakoutData, keeperData] = await Promise.all([
            lineupRes.json(), waiverRes.json(), breakoutRes.json(), keeperRes.json(),
          ])
        } else {
          const [lineupRes, waiverRes, breakoutRes, keeperRes] = await Promise.all([
            fetch(`${BASE_PATH}/api/daily_lineup.json`),
            fetch(`${BASE_PATH}/api/waiver_wire.json`),
            fetch(`${BASE_PATH}/api/breakouts.json`),
            fetch(`${BASE_PATH}/api/keepers.json`),
          ])

          if (!lineupRes.ok || !waiverRes.ok || !breakoutRes.ok || !keeperRes.ok) {
            throw new Error("One or more data files failed to load.")
          }

          ;[lineupData, waiverData, breakoutData, keeperData] = await Promise.all([
            lineupRes.json(), waiverRes.json(), breakoutRes.json(), keeperRes.json(),
          ])
        }

        setDailyLineup(lineupData)
        setWaiverWire(waiverData.targets || [])
        setBreakouts(breakoutData.alerts || [])
        setKeepers(keeperData.keepers || [])

        // Use the actual generated_at timestamp from the JSON, falling back
        // to the waiver or breakout timestamp
        const ts =
          lineupData.generated_at ||
          waiverData.generated_at ||
          breakoutData.generated_at ||
          null
        setDataTimestamp(ts)
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load dashboard data."
        setError(msg)
        console.error("Error fetching dashboard data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const fetchLineupFocus = useCallback(async () => {
    try {
      const res = await fetch(`${DRAFT_API_BASE}/season/lineup-focus`, { cache: "no-store" })
      if (!res.ok) return
      setLineupFocus(await res.json())
    } catch {
      // Server not running — silently ignore
    }
  }, [])

  useEffect(() => {
    fetchLineupFocus()
    const t = setInterval(() => fetchLineupFocus(), 60_000)
    return () => clearInterval(t)
  }, [fetchLineupFocus])

  const copyLineupToClipboard = () => {
    const mustStart = dailyLineup.must_start.map(p => `${p.player} (${p.confidence})`).join('\n')
    const start = dailyLineup.start.map(p => `${p.player} (${p.confidence})`).join('\n')
    const text = `Daily Lineup - ${new Date().toLocaleDateString()}\n\nMUST START:\n${mustStart}\n\nSTART:\n${start}`
    navigator.clipboard.writeText(text)
    toast({ title: "Lineup Copied!", description: "Your lineup has been copied to clipboard." })
  }

  const filterPlayers = useCallback((players: Player[]) => {
    return players.filter(p => {
      const matchesSearch =
        p.player.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.team.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesPosition =
        positionFilter === "all" ||
        p.position.split(',').map(s => s.trim()).includes(positionFilter)
      const matchesConfidence = p.confidence >= confidenceThreshold
      return matchesSearch && matchesPosition && matchesConfidence
    })
  }, [searchTerm, positionFilter, confidenceThreshold])

  const filteredMustStart = useMemo(() => filterPlayers(dailyLineup.must_start), [dailyLineup.must_start, filterPlayers])
  const filteredStart = useMemo(() => filterPlayers(dailyLineup.start), [dailyLineup.start, filterPlayers])
  const filteredFlex = useMemo(() => filterPlayers(dailyLineup.flex), [dailyLineup.flex, filterPlayers])
  const filteredBench = useMemo(() => filterPlayers(dailyLineup.bench), [dailyLineup.bench, filterPlayers])

  const totalPlayingCount = dailyLineup.must_start.length + dailyLineup.start.length + dailyLineup.flex.length
  const filteredCount = filteredMustStart.length + filteredStart.length + filteredFlex.length + filteredBench.length
  const activeRosterPlayers = [...dailyLineup.must_start, ...dailyLineup.start, ...dailyLineup.flex, ...dailyLineup.bench]

  const formattedTimestamp = useMemo(() => {
    if (!dataTimestamp) return null
    try {
      return new Date(dataTimestamp).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
      })
    } catch {
      return null
    }
  }, [dataTimestamp])

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <header className="mb-8">
            <h1 className="text-4xl font-bold tracking-tight mb-2">⚾ Baseball Dashboard</h1>
            <p className="text-muted-foreground text-lg">Loading your competitive advantage...</p>
          </header>
          <DashboardSkeleton />
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <CommandPalette
          rosterPlayers={activeRosterPlayers}
          notPlayingPlayers={dailyLineup.not_playing}
          waiverPlayers={waiverWire}
          breakoutPlayers={breakouts}
          onSelectPlayer={(player) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setSelectedPlayer(player as any)
            setDetailsOpen(true)
          }}
        />

        <PlayerDetailDialog
          player={selectedPlayer}
          open={detailsOpen}
          onOpenChange={setDetailsOpen}
        />

        {/* Header */}
        <header className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight mb-1">⚾ Baseball Dashboard</h1>
              <p className="text-muted-foreground text-sm">
                Auto-updates daily at 8am ET • Press{" "}
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground">
                  ⌘K
                </kbd>{" "}
                to search
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Link href="/draft">
                <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground">
                  <Star className="h-4 w-4" />
                  Draft
                </Button>
              </Link>
              <Link href="/draft/live">
                <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground">
                  <Zap className="h-3.5 w-3.5" />
                  Live Draft
                </Button>
              </Link>
              <Link href="/matchup">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Swords className="h-4 w-4" />
                  Matchup
                </Button>
              </Link>
              <Link href="/standings">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Trophy className="h-4 w-4" />
                  Standings
                </Button>
              </Link>
              <Link href="/closers">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Shield className="h-4 w-4" />
                  Closers
                </Button>
              </Link>
              <Link href="/trajectory">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <TrendingUp className="h-4 w-4" />
                  Trajectory
                </Button>
              </Link>
              {formattedTimestamp && (
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span className="hidden sm:inline">Data: {formattedTimestamp}</span>
                </div>
              )}
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium">Data failed to load.</span> {error}
              {" "}Check that the GitHub Actions workflow ran successfully and the JSON files are up to date.
            </div>
          </div>
        )}

        {/* Lineup Focus Banner */}
        {lineupFocus && lineupFocus.season_started && lineupFocus.swing_categories.length > 0 && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <Swords className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wide">
                Week {lineupFocus.week}: Focus Here
              </span>
            </div>
            <div className="flex flex-wrap gap-3">
              {lineupFocus.swing_categories.map(cat => (
                <div key={cat.stat_id} className="flex items-center gap-1.5 text-sm">
                  <span className={`font-bold ${cat.status === "close_loss" ? "text-red-400" : "text-emerald-400"}`}>
                    {cat.stat_name}
                  </span>
                  <span className="text-slate-500 text-xs">
                    ({cat.my_value ?? "–"} vs {cat.opp_value ?? "–"})
                  </span>
                  {cat.focus_players.length > 0 && (
                    <span className="text-slate-400 text-xs">— {cat.focus_players.slice(0, 2).join(", ")}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filter Bar */}
        {totalPlayingCount > 0 && (
          <FilterBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            positionFilter={positionFilter}
            onPositionFilterChange={setPositionFilter}
            confidenceThreshold={confidenceThreshold}
            onConfidenceThresholdChange={setConfidenceThreshold}
            onClearFilters={() => {
              setSearchTerm("")
              setPositionFilter("all")
              setConfidenceThreshold(0)
            }}
            playerCount={filteredCount}
          />
        )}

        {/* Main Content */}
        {totalPlayingCount === 0 && !error ? (
          <>
            {/* No-Lineup Layout (off-day or early morning before schedule loads) */}
            <div className="space-y-6">
              <WaiverWireTable targets={waiverWire} />
              <BreakoutDetectorTable alerts={breakouts} />
              {waiverWire.length === 0 && breakouts.length === 0 && keepers.length === 0 && (
                <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed">
                  <Calendar className="h-16 w-16 mx-auto mb-4 opacity-30" />
                  <p className="mb-2 text-lg font-medium">No data yet for today</p>
                  <p className="text-sm">
                    Run:{" "}
                    <code className="bg-muted px-2 py-1 rounded">python scripts/export_dashboard_data.py</code>
                  </p>
                </div>
              )}
              {keepers.length > 0 && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-start pl-0 hover:bg-transparent font-semibold text-base gap-2">
                      <ChevronDown className="h-4 w-4" />
                      <Star className="h-4 w-4 text-muted-foreground" />
                      <span>Keeper Projections</span>
                      <span className="text-xs text-muted-foreground font-normal ml-1">(next offseason)</span>
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3">
                    <KeeperAnalyzerTable recommendations={keepers.map(k => ({
                      ...k,
                      round: String(k.round),
                    }))} />
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>

            {dailyLineup.not_playing.length > 0 && (
              <div className="mt-6">
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-start pl-0 hover:bg-transparent font-semibold text-base">
                      <ChevronDown className="mr-2 h-4 w-4" />
                      Not Playing Today ({dailyLineup.not_playing.length})
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3">
                    <NotPlayingTable players={dailyLineup.not_playing} />
                  </CollapsibleContent>
                </Collapsible>
              </div>
            )}
          </>
        ) : (
          <>
            {/* In-Season Layout */}
            <div className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    <Users className="h-5 w-5 text-primary" />
                    Daily Lineup
                  </h2>
                  <Button variant="outline" size="sm" onClick={copyLineupToClipboard}>
                    <Copy className="mr-2 h-4 w-4" />
                    Copy
                  </Button>
                </div>

                <Tabs defaultValue="lineup" className="w-full">
                  <TabsList className="mb-4">
                    <TabsTrigger value="lineup">Lineup</TabsTrigger>
                    <TabsTrigger value="analysis">Analysis ({filteredCount})</TabsTrigger>
                    <TabsTrigger value="bench">Bench ({filteredBench.length})</TabsTrigger>
                  </TabsList>

                  {/* Optimal position-slot view */}
                  <TabsContent value="lineup">
                    <OptimalLineupView players={activeRosterPlayers} />
                  </TabsContent>

                  {/* Flat confidence-sorted list with filter bar */}
                  <TabsContent value="analysis" className="space-y-4">
                    {filteredMustStart.length > 0 && (
                      <div className="space-y-2">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Must Start</h3>
                        <PlayerTable players={filteredMustStart} variant="must-start" />
                      </div>
                    )}
                    {filteredStart.length > 0 && (
                      <div className="space-y-2">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Start</h3>
                        <PlayerTable players={filteredStart} variant="start" />
                      </div>
                    )}
                    {filteredFlex.length > 0 && (
                      <div className="space-y-2">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Flex</h3>
                        <PlayerTable players={filteredFlex} variant="flex" />
                      </div>
                    )}
                  </TabsContent>

                  {/* Bench — players below confidence threshold */}
                  <TabsContent value="bench">
                    {filteredBench.length > 0
                      ? <PlayerTable players={filteredBench} variant="bench" />
                      : <p className="py-8 text-center text-sm text-muted-foreground">No bench players today</p>
                    }
                  </TabsContent>
                </Tabs>

                {dailyLineup.not_playing.length > 0 && (
                  <div className="mt-6">
                    <Collapsible>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" className="w-full justify-start pl-0 hover:bg-transparent font-semibold text-base">
                          <ChevronDown className="mr-2 h-4 w-4" />
                          Not Playing Today ({dailyLineup.not_playing.length})
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-3">
                        <NotPlayingTable players={dailyLineup.not_playing} />
                      </CollapsibleContent>
                    </Collapsible>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                <WaiverWireTable targets={waiverWire} />
                <BreakoutDetectorTable alerts={breakouts} />
              </div>
            </div>
          </>
        )}

        <footer className="mt-12 text-center text-sm text-muted-foreground">
          <p>Built with Next.js • Powered by Statcast • Deployed on GitHub Pages</p>
          <p className="mt-1">🏆 Your year-round competitive advantage</p>
        </footer>
      </div>
    </main>
  )
}

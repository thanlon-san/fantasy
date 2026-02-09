"use client"

import { useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, Users, Calendar, Copy } from "lucide-react"
import { useState, useEffect, useMemo } from "react"
import { PlayerTable } from "@/components/player-table"
import { NotPlayingTable } from "@/components/not-playing-table"
import { DashboardSkeleton } from "@/components/loading-skeleton"
import { CommandPalette } from "@/components/command-palette"
import { FilterBar } from "@/components/filter-bar"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import { useToast } from "@/components/ui/use-toast"
import { ThemeToggle } from "@/components/theme-toggle"
import { WaiverWireTable } from "@/components/waiver-wire-table"
import { BreakoutDetectorTable } from "@/components/breakout-detector-table"

// API base URL - use environment variable or fallback to local
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// For static JSON fallback during development
const BASE_PATH = process.env.NODE_ENV === 'production' ? '/fantasy/baseball' : ''
const USE_API = process.env.NEXT_PUBLIC_USE_API === 'true'

// Type definitions
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
  // Legacy keeper fields (may not exist in new format)
  adp?: number
  value_gain?: number
  drop_player_adp?: number
  keeper_cost?: number
  // New in-season value fields
  rostered_pct?: number
  trending?: "HOT" | "COLD" | "STABLE"
  last_7_days?: {
    avg?: number
    hr?: number
    rbi?: number
    sb?: number
    era?: number
    whip?: number
    k?: number
    w?: number
    games?: number
  }
  last_14_days?: {
    avg?: number
    hr?: number
    rbi?: number
    sb?: number
    era?: number
    whip?: number
    k?: number
    w?: number
    games?: number
  }
  last_30_days?: {
    avg?: number
    hr?: number
    rbi?: number
    sb?: number
    era?: number
    whip?: number
    k?: number
    w?: number
    games?: number
  }
  statcast_changes?: {
    exit_velo?: string
    hard_hit_pct?: string
    barrel_rate?: string
    velo?: string
    chase_rate?: string
    whiff_rate?: string
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
  round: string
  adp: number
  surplus: string
  value: string
}

export default function Home() {
  const { toast } = useToast()

  // Filter State
  const [searchTerm, setSearchTerm] = useState("")
  const [positionFilter, setPositionFilter] = useState("all")
  const [confidenceThreshold, setConfidenceThreshold] = useState(0)
  
  // Search Dialog State
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)

  // State for real data
  const [dailyLineup, setDailyLineup] = useState<{
    must_start: Player[]
    start: Player[]
    flex: Player[]
    bench: Player[]
    not_playing: { player: string; position: string; team: string; adp?: number }[]
    summary?: { total_roster: number; playing_today: number; not_playing: number }
  }>({
    must_start: [],
    start: [],
    flex: [],
    bench: [],
    not_playing: []
  })
  const [waiverWire, setWaiverWire] = useState<WaiverTarget[]>([])
  const [breakouts, setBreakouts] = useState<Breakout[]>([])
  const [keepers, setKeepers] = useState<Keeper[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  // Fetch real data on mount
  useEffect(() => {
    async function fetchData() {
      try {
        if (USE_API) {
          // Fetch from live API
          const [lineupRes, waiverRes, breakoutRes, keeperRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/lineup`),
            fetch(`${API_BASE_URL}/api/waivers`),
            fetch(`${API_BASE_URL}/api/breakouts`),
            fetch(`${API_BASE_URL}/api/keepers`),
          ])

          const lineupData = await lineupRes.json()
          const waiverData = await waiverRes.json()
          const breakoutData = await breakoutRes.json()
          const keeperData = await keeperRes.json()

          setDailyLineup(lineupData)
          setWaiverWire(waiverData.targets || [])
          setBreakouts(breakoutData.alerts || [])
          setKeepers(keeperData.keepers || [])
        } else {
          // Fallback to static JSON files
          const [lineupRes, waiverRes, breakoutRes, keeperRes] = await Promise.all([
            fetch(`${BASE_PATH}/api/daily_lineup.json`),
            fetch(`${BASE_PATH}/api/waiver_wire.json`),
            fetch(`${BASE_PATH}/api/breakouts.json`),
            fetch(`${BASE_PATH}/api/keepers.json`),
          ])

          const lineupData = await lineupRes.json()
          const waiverData = await waiverRes.json()
          const breakoutData = await breakoutRes.json()
          const keeperData = await keeperRes.json()

          setDailyLineup(lineupData)
          setWaiverWire(waiverData.targets || [])
          setBreakouts(breakoutData.alerts || [])
          setKeepers(keeperData.keepers || [])
        }
        setLastUpdated(new Date())
      } catch (error) {
        console.error('Error fetching dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const copyLineupToClipboard = () => {
    const mustStart = dailyLineup.must_start.map(p => `${p.player} (${p.confidence})`).join('\n')
    const start = dailyLineup.start.map(p => `${p.player} (${p.confidence})`).join('\n')
    const text = `Daily Lineup - ${new Date().toLocaleDateString()}\n\nMUST START:\n${mustStart}\n\nSTART:\n${start}`
    navigator.clipboard.writeText(text)
    
    toast({
      title: "Lineup Copied!",
      description: "Your lineup has been copied to clipboard.",
    })
  }

  // Derived filtered lists - use useCallback to prevent recreation on every render
  const filterPlayers = useCallback((players: Player[]) => {
    return players.filter(p => {
      const matchesSearch = p.player.toLowerCase().includes(searchTerm.toLowerCase()) || 
                            p.team.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesPosition = positionFilter === "all" || p.position === positionFilter
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
  const allPlayers = [...dailyLineup.must_start, ...dailyLineup.start, ...dailyLineup.flex, ...dailyLineup.bench]

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <header className="mb-8">
            <h1 className="text-4xl font-bold tracking-tight mb-2">
              ⚾ Baseball Dashboard
            </h1>
            <p className="text-muted-foreground text-lg">
              Loading your competitive advantage...
            </p>
          </header>
          <DashboardSkeleton />
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Command Palette */}
        <CommandPalette 
          players={allPlayers} 
          onSelectPlayer={(player) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setSelectedPlayer(player as any)
            setDetailsOpen(true)
          }}
        />
        
        {/* Detail Dialog (Global for search) */}
        <PlayerDetailDialog 
          player={selectedPlayer}
          open={detailsOpen}
          onOpenChange={setDetailsOpen}
        />

        {/* Header */}
        <header className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight mb-1">
                ⚾ Baseball Dashboard
              </h1>
              <p className="text-muted-foreground text-sm">
                Auto-updates daily at 8am ET • Press <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground">⌘K</kbd> to search
              </p>
            </div>
            <div className="flex items-center gap-3">
              {lastUpdated && (
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span className="hidden sm:inline">{lastUpdated.toLocaleDateString()}</span>
                </div>
              )}
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Conditional Filter Bar - Only show when there are players */}
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

        {/* Main Content - Adaptive Layout */}
        {totalPlayingCount === 0 && dailyLineup.not_playing.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed">
            <Calendar className="h-16 w-16 mx-auto mb-4 opacity-30" />
            <p className="mb-2 text-lg font-medium">No lineup data available</p>
            <p className="text-sm">Run: <code className="bg-muted px-2 py-1 rounded">python scripts/export_dashboard_data.py</code></p>
          </div>
        ) : totalPlayingCount === 0 ? (
          <>
            {/* Off-Season Layout: Full Width Priority */}
            <div className="space-y-6">
              <WaiverWireTable targets={waiverWire} />
              <BreakoutDetectorTable alerts={breakouts} />
            </div>

            {/* Not Playing - Collapsible */}
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
            {/* In-Season Layout: Daily Lineup Priority */}
            <div className="space-y-6">
              {/* Daily Lineup Section */}
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

                <Tabs defaultValue="all" className="w-full">
                <TabsList className="mb-4">
                  <TabsTrigger value="all">All ({filteredCount})</TabsTrigger>
                  <TabsTrigger value="must-start">Must Start ({filteredMustStart.length})</TabsTrigger>
                  <TabsTrigger value="start">Start ({filteredStart.length})</TabsTrigger>
                  <TabsTrigger value="flex">Flex ({filteredFlex.length})</TabsTrigger>
                  <TabsTrigger value="bench">Bench ({filteredBench.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-4">
                  {filteredMustStart.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
                        Must Start
                      </h3>
                      <PlayerTable players={filteredMustStart} variant="must-start" />
                    </div>
                  )}
                  
                  {filteredStart.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold flex items-center gap-2">
                        Start
                      </h3>
                      <PlayerTable players={filteredStart} variant="start" />
                    </div>
                  )}
                  
                  {filteredFlex.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold flex items-center gap-2">
                        Flex
                      </h3>
                      <PlayerTable players={filteredFlex} variant="flex" />
                    </div>
                  )}
                  
                  {filteredBench.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-yellow-700 dark:text-yellow-400 flex items-center gap-2">
                        Consider Benching
                      </h3>
                      <PlayerTable players={filteredBench} variant="bench" />
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="must-start">
                  <PlayerTable players={filteredMustStart} variant="must-start" />
                </TabsContent>

                <TabsContent value="start">
                  <PlayerTable players={filteredStart} variant="start" />
                </TabsContent>

                <TabsContent value="flex">
                  <PlayerTable players={filteredFlex} variant="flex" />
                </TabsContent>

                <TabsContent value="bench">
                  <PlayerTable players={filteredBench} variant="bench" />
                </TabsContent>
              </Tabs>

              {/* Not Playing Section */}
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

            {/* Insights Panel Below Lineup */}
            <div className="space-y-6 mt-6">
              <WaiverWireTable targets={waiverWire} />
              <BreakoutDetectorTable alerts={breakouts} />
            </div>
          </div>
          </>
        )}

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-muted-foreground">
          <p>Built with Next.js • Powered by Statcast • Deployed on GitHub Pages</p>
          <p className="mt-1">🏆 Your year-round competitive advantage</p>
        </footer>
      </div>
    </main>
  )
}

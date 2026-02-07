"use client"

import { useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, ChevronUp, TrendingUp, Users, Target, Star, Calendar, Copy, Search as SearchIcon } from "lucide-react"
import { useState, useEffect, useMemo } from "react"
import { PlayerTable } from "@/components/player-table"
import { NotPlayingTable } from "@/components/not-playing-table"
import { DashboardSkeleton } from "@/components/loading-skeleton"
import { CommandPalette } from "@/components/command-palette"
import { FilterBar } from "@/components/filter-bar"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import { useToast } from "@/components/ui/use-toast"

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
  adp: number
  value_gain: number
  drop_player: string
  drop_player_position: string
  drop_player_adp: number
  confidence: string
  reason: string
  keeper_cost: number
}

type Breakout = {
  player: string
  signal: string
  stat: string
  category: string
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
  const [expandedSections, setExpandedSections] = useState({
    waivers: false,
    breakouts: false,
    keepers: false,
  })

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

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const copyLineupToClipboard = () => {
    const mustStart = dailyLineup.must_start.map(p => `🔥 ${p.player} (${p.confidence})`).join('\n')
    const start = dailyLineup.start.map(p => `✅ ${p.player} (${p.confidence})`).join('\n')
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
        <header className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-4xl font-bold tracking-tight mb-2">
                ⚾ Baseball Dashboard
              </h1>
              <p className="text-muted-foreground text-lg">
                Your year-round competitive advantage • Auto-updates daily at 8am ET
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Press <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                  <span className="text-xs">⌘</span>K
                </kbd> to search
              </p>
            </div>
            {lastUpdated && (
              <div className="text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span>Updated: {lastUpdated.toLocaleString()}</span>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Quick Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Playing Today</CardTitle>
              <Users className="h-5 w-5 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalPlayingCount}</div>
              <p className="text-xs text-muted-foreground">
                {dailyLineup.summary?.total_roster || 0} total roster
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Must Start</CardTitle>
              <TrendingUp className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{dailyLineup.must_start.length}</div>
              <p className="text-xs text-muted-foreground">High confidence plays</p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Breakouts</CardTitle>
              <TrendingUp className="h-5 w-5 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{breakouts.filter((b) => b.signal === "STRONG").length}</div>
              <p className="text-xs text-muted-foreground">STRONG signals</p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Waiver Targets</CardTitle>
              <Target className="h-5 w-5 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{waiverWire.length}</div>
              <p className="text-xs text-muted-foreground">High-value pickups</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
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

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Daily Lineup - FULL WIDTH WITH TABS */}
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-6 w-6 text-primary" />
                  <div className="flex-1">
                    <CardTitle>Daily Lineup Recommendations</CardTitle>
                    <CardDescription>Optimized for today&apos;s matchups • Sort by any column</CardDescription>
                  </div>
                </div>
                {totalPlayingCount > 0 && (
                  <Button variant="outline" size="sm" onClick={copyLineupToClipboard}>
                    <Copy className="mr-2 h-4 w-4" />
                    Copy Lineup
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {totalPlayingCount === 0 && dailyLineup.not_playing.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="mb-2 text-lg font-medium">No lineup data available</p>
                  <p className="text-sm">Run: <code className="bg-muted px-2 py-1 rounded">python scripts/export_dashboard_data.py</code></p>
                </div>
              ) : totalPlayingCount === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="mb-2 text-lg font-medium">No games scheduled today</p>
                  <p className="text-sm">Check back tomorrow for lineup recommendations</p>
                </div>
              ) : (
                <Tabs defaultValue="all" className="w-full">
                  <TabsList className="grid w-full grid-cols-5 mb-4">
                    <TabsTrigger value="all" className="gap-1 text-xs md:text-sm px-1">
                      All <Badge variant="secondary" className="ml-1 hidden md:inline-flex">{filteredCount}</Badge>
                    </TabsTrigger>
                    <TabsTrigger value="must-start" className="gap-1 text-xs md:text-sm px-1">
                      Must Start <Badge variant="secondary" className="ml-1 hidden md:inline-flex bg-green-100 text-green-800">{filteredMustStart.length}</Badge>
                    </TabsTrigger>
                    <TabsTrigger value="start" className="gap-1 text-xs md:text-sm px-1">
                      Start <Badge variant="secondary" className="ml-1 hidden md:inline-flex">{filteredStart.length}</Badge>
                    </TabsTrigger>
                    <TabsTrigger value="flex" className="gap-1 text-xs md:text-sm px-1">
                      Flex <Badge variant="secondary" className="ml-1 hidden md:inline-flex">{filteredFlex.length}</Badge>
                    </TabsTrigger>
                    <TabsTrigger value="bench" className="gap-1 text-xs md:text-sm px-1">
                      Bench <Badge variant="secondary" className="ml-1 hidden md:inline-flex bg-yellow-100 text-yellow-800">{filteredBench.length}</Badge>
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="all" className="space-y-4">
                    {filteredMustStart.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2 text-green-700 dark:text-green-400">
                          🔥 Must Start ({filteredMustStart.length})
                        </h3>
                        <PlayerTable players={filteredMustStart} variant="must-start" />
                      </div>
                    )}
                    
                    {filteredStart.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                          ✅ Start ({filteredStart.length})
                        </h3>
                        <PlayerTable players={filteredStart} variant="start" />
                      </div>
                    )}
                    
                    {filteredFlex.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                          ➡️ Flex ({filteredFlex.length})
                        </h3>
                        <PlayerTable players={filteredFlex} variant="flex" />
                      </div>
                    )}
                    
                    {filteredBench.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                          ⚠️ Consider Benching ({filteredBench.length})
                        </h3>
                        <PlayerTable players={filteredBench} variant="bench" />
                      </div>
                    )}
                    
                    {filteredCount === 0 && (
                      <div className="text-center py-12 text-muted-foreground border rounded-lg border-dashed">
                        <SearchIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No players match your filters</p>
                        <Button variant="link" onClick={() => {
                          setSearchTerm("")
                          setPositionFilter("all")
                          setConfidenceThreshold(0)
                        }}>Clear Filters</Button>
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
              )}

              {/* Not Playing Section */}
              {dailyLineup.not_playing.length > 0 && (
                <div className="mt-6">
                  <Collapsible>
                    <CollapsibleTrigger asChild>
                      <Button variant="outline" className="w-full">
                        <ChevronDown className="mr-2 h-4 w-4" />
                        💤 Not Playing Today ({dailyLineup.not_playing.length})
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-4">
                      <NotPlayingTable players={dailyLineup.not_playing} />
                    </CollapsibleContent>
                  </Collapsible>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Waiver Wire - Expandable */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Target className="h-6 w-6 text-purple-600" />
                <div className="flex-1">
                  <CardTitle>Waiver Wire</CardTitle>
                  <CardDescription>Top pickup targets</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {waiverWire.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No waiver recommendations</p>
                </div>
              ) : (
                <Collapsible open={expandedSections.waivers} onOpenChange={() => toggleSection('waivers')}>
                  {/* Preview (first 3) */}
                  <div className="space-y-3 mb-3">
                    {waiverWire.slice(0, 3).map((target, i) => (
                      <div key={i} className="p-4 rounded-lg border-2 border-muted hover:border-purple-200 dark:hover:border-purple-800 bg-card transition-all">
                        {/* Header with confidence */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                            Waiver Recommendation
                          </div>
                          <Badge className={target.confidence === "STRONG" ? "bg-purple-600" : "bg-purple-500"}>
                            {target.confidence}
                          </Badge>
                        </div>

                        {/* ADD Section */}
                        <div className="mb-3 pb-3 border-b">
                          <div className="text-xs font-medium text-green-700 dark:text-green-400 mb-1 flex items-center gap-1">
                            <span className="text-base">➕</span>
                            ADD
                          </div>
                          <div className="pl-6">
                            <div className="font-bold text-lg">{target.player}</div>
                            <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-2 mt-1">
                              <Badge variant="secondary">{target.position}</Badge>
                              <span>{target.team}</span>
                              <span className="text-xs">•</span>
                              <span className="font-medium">ADP {target.adp}</span>
                              {target.keeper_cost && (
                                <>
                                  <span className="text-xs">•</span>
                                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                                    Keep in Rd {target.keeper_cost}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Value Gain Callout */}
                        <div className="my-3 p-2 bg-green-50 dark:bg-green-950/20 rounded-md border border-green-200 dark:border-green-800">
                          <div className="text-center">
                            <div className="text-xs text-muted-foreground mb-1">Value Gain</div>
                            <div className="text-xl font-bold text-green-600 dark:text-green-400">
                              +{target.value_gain} ADP
                            </div>
                          </div>
                        </div>

                        {/* DROP Section */}
                        <div className="mb-3 pb-3 border-b">
                          <div className="text-xs font-medium text-red-700 dark:text-red-400 mb-1 flex items-center gap-1">
                            <span className="text-base">➖</span>
                            DROP
                          </div>
                          <div className="pl-6">
                            <div className="font-semibold text-base">{target.drop_player}</div>
                            {target.drop_player_position && target.drop_player_adp && (
                              <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                                <Badge variant="outline">{target.drop_player_position}</Badge>
                                <span className="font-medium">ADP {target.drop_player_adp}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Reason */}
                        <div className="text-xs text-muted-foreground">
                          <div className="font-medium mb-1">Why this move:</div>
                          <div className="space-y-0.5">
                            {target.reason.split(',').map((r, idx) => (
                              <div key={idx} className="flex items-start gap-1">
                                <span className="text-purple-600 dark:text-purple-400">•</span>
                                <span>{r.trim().replace('🎯 ', '')}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Expandable Content */}
                  {waiverWire.length > 3 && (
                    <>
                      <CollapsibleContent>
                        <div className="space-y-3 mb-3">
                          {waiverWire.slice(3).map((target, i) => (
                            <div key={i} className="p-4 rounded-lg border-2 border-muted hover:border-purple-200 dark:hover:border-purple-800 bg-card transition-all">
                              {/* Header with confidence */}
                              <div className="flex items-center justify-between mb-3">
                                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                  Waiver Recommendation
                                </div>
                                <Badge className={target.confidence === "STRONG" ? "bg-purple-600" : "bg-purple-500"}>
                                  {target.confidence}
                                </Badge>
                              </div>

                              {/* ADD Section */}
                              <div className="mb-3 pb-3 border-b">
                                <div className="text-xs font-medium text-green-700 dark:text-green-400 mb-1 flex items-center gap-1">
                                  <span className="text-base">➕</span>
                                  ADD
                                </div>
                                <div className="pl-6">
                                  <div className="font-bold text-lg">{target.player}</div>
                                  <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-2 mt-1">
                                    <Badge variant="secondary">{target.position}</Badge>
                                    <span>{target.team}</span>
                                    <span className="text-xs">•</span>
                                    <span className="font-medium">ADP {target.adp}</span>
                                    {target.keeper_cost && (
                                      <>
                                        <span className="text-xs">•</span>
                                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                                          Keep in Rd {target.keeper_cost}
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* Value Gain Callout */}
                              <div className="my-3 p-2 bg-green-50 dark:bg-green-950/20 rounded-md border border-green-200 dark:border-green-800">
                                <div className="text-center">
                                  <div className="text-xs text-muted-foreground mb-1">Value Gain</div>
                                  <div className="text-xl font-bold text-green-600 dark:text-green-400">
                                    +{target.value_gain} ADP
                                  </div>
                                </div>
                              </div>

                              {/* DROP Section */}
                              <div className="mb-3 pb-3 border-b">
                                <div className="text-xs font-medium text-red-700 dark:text-red-400 mb-1 flex items-center gap-1">
                                  <span className="text-base">➖</span>
                                  DROP
                                </div>
                                <div className="pl-6">
                                  <div className="font-semibold text-base">{target.drop_player}</div>
                                  {target.drop_player_position && target.drop_player_adp && (
                                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                                      <Badge variant="outline">{target.drop_player_position}</Badge>
                                      <span className="font-medium">ADP {target.drop_player_adp}</span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Reason */}
                              <div className="text-xs text-muted-foreground">
                                <div className="font-medium mb-1">Why this move:</div>
                                <div className="space-y-0.5">
                                  {target.reason.split(',').map((r, idx) => (
                                    <div key={idx} className="flex items-start gap-1">
                                      <span className="text-purple-600 dark:text-purple-400">•</span>
                                      <span>{r.trim().replace('🎯 ', '')}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>

                      <CollapsibleTrigger asChild>
                        <Button variant="outline" className="w-full">
                          {expandedSections.waivers ? (
                            <>
                              <ChevronUp className="mr-2 h-4 w-4" />
                              Show Less
                            </>
                          ) : (
                            <>
                              <ChevronDown className="mr-2 h-4 w-4" />
                              Show All {waiverWire.length} Targets
                            </>
                          )}
                        </Button>
                      </CollapsibleTrigger>
                    </>
                  )}
                </Collapsible>
              )}
            </CardContent>
          </Card>

          {/* Breakout Detector - Expandable */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-6 w-6 text-orange-600" />
                <div className="flex-1">
                  <CardTitle>Breakout Detector</CardTitle>
                  <CardDescription>Statcast-powered alerts</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Collapsible open={expandedSections.breakouts} onOpenChange={() => toggleSection('breakouts')}>
                <div className="space-y-2 mb-3">
                  {breakouts.map((player, i) => (
                    <div key={i} className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between mb-1">
                        <div className="font-semibold">{player.player}</div>
                        <Badge className={player.signal === "STRONG" ? "bg-orange-600" : "bg-amber-600"}>
                          {player.signal}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">{player.stat}</div>
                      <div className="text-xs text-muted-foreground mt-1">{player.category} breakout</div>
                    </div>
                  ))}
                </div>

                <CollapsibleTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <ChevronDown className="mr-2 h-4 w-4" />
                    Scan Free Agents
                  </Button>
                </CollapsibleTrigger>
              </Collapsible>
            </CardContent>
          </Card>

          {/* Keeper Analyzer - Expandable */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Star className="h-6 w-6 text-emerald-600" />
                <div className="flex-1">
                  <CardTitle>Keeper Analyzer</CardTitle>
                  <CardDescription>Optimize selections</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Collapsible open={expandedSections.keepers} onOpenChange={() => toggleSection('keepers')}>
                <div className="space-y-2 mb-3">
                  {keepers.slice(0, 3).map((keeper, i) => (
                    <div key={i} className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="font-semibold">{keeper.player}</div>
                        <Badge className="bg-emerald-600">{keeper.value}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mb-1">
                        Keep in {keeper.round} (ADP: {keeper.adp})
                      </div>
                      <div className="text-lg font-bold text-emerald-600">{keeper.surplus}</div>
                    </div>
                  ))}
                </div>

                {keepers.length > 3 && (
                  <>
                    <CollapsibleContent>
                      <div className="space-y-2 mb-3">
                        {keepers.slice(3).map((keeper, i) => (
                          <div key={i} className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                            <div className="flex items-start justify-between mb-2">
                              <div className="font-semibold">{keeper.player}</div>
                              <Badge className="bg-emerald-600">{keeper.value}</Badge>
                            </div>
                            <div className="text-sm text-muted-foreground mb-1">
                              Keep in {keeper.round} (ADP: {keeper.adp})
                            </div>
                            <div className="text-lg font-bold text-emerald-600">{keeper.surplus}</div>
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>

                    <CollapsibleTrigger asChild>
                      <Button variant="outline" className="w-full">
                        {expandedSections.keepers ? (
                          <>
                            <ChevronUp className="mr-2 h-4 w-4" />
                            Show Less
                          </>
                        ) : (
                          <>
                            <ChevronDown className="mr-2 h-4 w-4" />
                            Show All {keepers.length} Keepers
                          </>
                        )}
                      </Button>
                    </CollapsibleTrigger>
                  </>
                )}
              </Collapsible>
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-muted-foreground">
          <p>Built with Next.js • Powered by Statcast • Deployed on GitHub Pages</p>
          <p className="mt-1">🏆 Your year-round competitive advantage</p>
        </footer>
      </div>
    </main>
  )
}

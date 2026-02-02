"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useState, useEffect } from "react"

// Base path for GitHub Pages
const BASE_PATH = process.env.NODE_ENV === 'production' ? '/fantasy/baseball' : ''

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
  adp: number
  reason: string
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
  const [expandedSections, setExpandedSections] = useState({
    waivers: false,
    breakouts: false,
    keepers: false,
  })

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
  const [, setLoading] = useState(true)

  // Fetch real data on mount
  useEffect(() => {
    async function fetchData() {
      try {
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

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return "bg-green-600"
    if (confidence >= 60) return "bg-yellow-600"
    return "bg-red-600"
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            ⚾ Baseball Dashboard
          </h1>
          <p className="text-muted-foreground text-lg">
            Your year-round competitive advantage
          </p>
        </header>

        {/* Quick Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Today&apos;s Games</CardTitle>
              <span className="text-2xl">📅</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">12</div>
              <p className="text-xs text-muted-foreground">MLB games scheduled</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Roster</CardTitle>
              <span className="text-2xl">👥</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dailyLineup.summary?.total_roster || 0}</div>
              <p className="text-xs text-muted-foreground">Players on roster</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Breakouts</CardTitle>
              <span className="text-2xl">🔥</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{breakouts.filter((b) => b.signal === "STRONG").length}</div>
              <p className="text-xs text-muted-foreground">STRONG signals</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Waiver Targets</CardTitle>
              <span className="text-2xl">🎯</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{waiverWire.length}</div>
              <p className="text-xs text-muted-foreground">High-value pickups</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Daily Lineup - FULL DISPLAY */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">📊</span>
                <div className="flex-1">
                  <CardTitle>Daily Lineup Recommendations</CardTitle>
                  <CardDescription>Optimized for today&apos;s matchups</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Must Start */}
              {dailyLineup.must_start.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    🔥 Must Start ({dailyLineup.must_start.length})
                  </h3>
                  <div className="space-y-2">
                    {dailyLineup.must_start.map((player, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-green-200 bg-green-50 dark:bg-green-950/30 dark:border-green-900 hover:bg-green-100 dark:hover:bg-green-950/50 transition-colors">
                        <div className="flex items-center gap-3 flex-1">
                          <Badge className="bg-green-600">{player.confidence}</Badge>
                          <div className="flex-1">
                            <div className="font-semibold">{player.player}</div>
                            <div className="text-sm text-muted-foreground">
                              {player.position} • {player.opponent} • {player.opponent_pitcher || 'TBD'}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">{player.reasons.join(', ')}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Start */}
              {dailyLineup.start.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    ✅ Start ({dailyLineup.start.length})
                  </h3>
                  <div className="space-y-2">
                    {dailyLineup.start.map((player, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                        <div className="flex items-center gap-3 flex-1">
                          <Badge className={getConfidenceColor(player.confidence)}>{player.confidence}</Badge>
                          <div className="flex-1">
                            <div className="font-semibold">{player.player}</div>
                            <div className="text-sm text-muted-foreground">
                              {player.position} • {player.opponent} • {player.opponent_pitcher || 'TBD'}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">{player.reasons.join(', ')}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Flex */}
              {dailyLineup.flex.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    ➡️ Flex ({dailyLineup.flex.length})
                  </h3>
                  <div className="space-y-2">
                    {dailyLineup.flex.map((player, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                        <div className="flex items-center gap-3 flex-1">
                          <Badge variant="secondary">{player.confidence}</Badge>
                          <div className="flex-1">
                            <div className="font-semibold">{player.player}</div>
                            <div className="text-sm text-muted-foreground">
                              {player.position} • {player.opponent} • {player.opponent_pitcher || 'TBD'}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Bench */}
              {dailyLineup.bench.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    ⚠️ Consider Benching ({dailyLineup.bench.length})
                  </h3>
                  <div className="space-y-2">
                    {dailyLineup.bench.map((player, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-yellow-200 bg-yellow-50 dark:bg-yellow-950/30 dark:border-yellow-900 hover:bg-yellow-100 dark:hover:bg-yellow-950/50 transition-colors">
                        <div className="flex items-center gap-3 flex-1">
                          <Badge className="bg-yellow-600">{player.confidence}</Badge>
                          <div className="flex-1">
                            <div className="font-semibold">{player.player}</div>
                            <div className="text-sm text-muted-foreground">
                              {player.position} • {player.opponent} • {player.opponent_pitcher || 'TBD'}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">{player.reasons.join(', ')}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Not Playing */}
              {dailyLineup.not_playing.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    💤 Not Playing Today ({dailyLineup.not_playing.length})
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {dailyLineup.not_playing.map((player, i) => (
                      <div key={i} className="p-2 rounded-lg border bg-muted/50 text-sm">
                        <div className="font-medium">{player.player}</div>
                        <div className="text-xs text-muted-foreground">{player.position} • {player.team}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty state */}
              {dailyLineup.must_start.length === 0 && dailyLineup.start.length === 0 && dailyLineup.flex.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="mb-2">No lineup data available</p>
                  <p className="text-sm">Run: <code className="bg-muted px-2 py-1 rounded">python scripts/export_dashboard_data.py</code></p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Waiver Wire - Expandable */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">🎯</span>
                <div className="flex-1">
                  <CardTitle>Waiver Wire</CardTitle>
                  <CardDescription>Top pickup targets</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Collapsible open={expandedSections.waivers} onOpenChange={() => toggleSection('waivers')}>
                {/* Preview (first 3) */}
                <div className="space-y-2 mb-3">
                  {waiverWire.slice(0, 3).map((player, i) => (
                    <div key={i} className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between mb-1">
                        <div className="font-semibold">{player.player}</div>
                        <Badge className="bg-purple-600">{player.position}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">{player.reason}</div>
                      <div className="text-xs text-muted-foreground mt-1">ADP: {player.adp}</div>
                    </div>
                  ))}
                </div>

                {/* Expandable Content */}
                <CollapsibleContent>
                  <div className="space-y-2 mb-3">
                    {waiverWire.slice(3).map((player, i) => (
                      <div key={i} className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                        <div className="flex items-start justify-between mb-1">
                          <div className="font-semibold">{player.player}</div>
                          <Badge className="bg-purple-600">{player.position}</Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">{player.reason}</div>
                        <div className="text-xs text-muted-foreground mt-1">ADP: {player.adp}</div>
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
              </Collapsible>
            </CardContent>
          </Card>

          {/* Breakout Detector - Expandable */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">🔬</span>
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
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">⭐</span>
                <div className="flex-1">
                  <CardTitle>Keeper Analyzer</CardTitle>
                  <CardDescription>Optimize your keeper selections</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Collapsible open={expandedSections.keepers} onOpenChange={() => toggleSection('keepers')}>
                <div className="grid md:grid-cols-3 gap-3 mb-3">
                  {keepers.map((keeper, i) => (
                    <div key={i} className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="font-semibold">{keeper.player}</div>
                        <Badge className="bg-emerald-600">{keeper.value}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mb-2">
                        Keep in {keeper.round} (ADP: {keeper.adp})
                      </div>
                      <div className="text-lg font-bold text-emerald-600">{keeper.surplus}</div>
                    </div>
                  ))}
                </div>

                <CollapsibleTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <ChevronDown className="mr-2 h-4 w-4" />
                    Analyze Full Roster
                  </Button>
                </CollapsibleTrigger>
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

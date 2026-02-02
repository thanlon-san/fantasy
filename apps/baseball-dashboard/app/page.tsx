"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useState } from "react"

// Sample data - will be replaced with API calls
const dailyLineup = {
  starters: [
    { player: "Mookie Betts", position: "2B", opponent: "vs COL (Freeland)", confidence: 92, matchup: "Excellent", parkFactor: "+15%", platoon: "Favorable" },
    { player: "Aaron Judge", position: "OF", opponent: "@ BAL (Kremer)", confidence: 88, matchup: "Good", parkFactor: "+8%", platoon: "Neutral" },
    { player: "Freddie Freeman", position: "1B", opponent: "vs COL (Freeland)", confidence: 85, matchup: "Good", parkFactor: "+15%", platoon: "Favorable" },
    { player: "Kyle Tucker", position: "OF", opponent: "vs SEA (Castillo)", confidence: 78, matchup: "Fair", parkFactor: "+3%", platoon: "Neutral" },
    { player: "Bo Bichette", position: "SS", opponent: "@ TB (Eflin)", confidence: 72, matchup: "Fair", parkFactor: "-5%", platoon: "Unfavorable" },
  ],
  bench: [
    { player: "Tyler O'Neill", position: "OF", opponent: "vs NYY (Cole)", confidence: 45, matchup: "Poor", parkFactor: "-8%", platoon: "Unfavorable" },
    { player: "Willy Adames", position: "SS", opponent: "@ LAD (Kershaw)", confidence: 38, matchup: "Poor", parkFactor: "-12%", platoon: "Unfavorable" },
  ]
}

const waiverWire = [
  { player: "Spencer Steer", position: "3B/OF", adp: 145, reason: "Hot streak + favorable schedule", signal: "Strong" },
  { player: "Bryan Reynolds", position: "OF", adp: 112, reason: "Undervalued, top-10 upside", signal: "Strong" },
  { player: "Vinnie Pasquantino", position: "1B", adp: 189, reason: "Breakout metrics, low ownership", signal: "Emerging" },
  { player: "Matt Chapman", position: "3B", adp: 167, reason: "Power surge + home games", signal: "Emerging" },
  { player: "Michael King", position: "SP", adp: 201, reason: "Rotation upgrade, Ks trending up", signal: "Emerging" },
]

const breakouts = [
  { player: "Elly De La Cruz", signal: "STRONG", stat: "Exit velo: 94.2 mph (↑3.5)", category: "Power" },
  { player: "Jackson Chourio", signal: "STRONG", stat: "Hard-hit%: 52% (↑12)", category: "Contact" },
  { player: "Wyatt Langford", signal: "EMERGING", stat: "Barrel%: 14.2% (↑6)", category: "Power" },
]

const keepers = [
  { player: "Mookie Betts", round: "R1", adp: 3, surplus: "+427 ADP", value: "Elite" },
  { player: "Kyle Tucker", round: "R3", adp: 15, surplus: "+239 ADP", value: "Strong" },
  { player: "Spencer Strider", round: "R12", adp: 48, surplus: "+96 ADP", value: "Excellent" },
]

export default function Home() {
  const [expandedSections, setExpandedSections] = useState({
    waivers: false,
    breakouts: false,
    keepers: false,
  })

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
              <CardTitle className="text-sm font-medium">Today's Games</CardTitle>
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
              <div className="text-2xl font-bold">{dailyLineup.starters.length + dailyLineup.bench.length}</div>
              <p className="text-xs text-muted-foreground">Players analyzed</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Breakouts</CardTitle>
              <span className="text-2xl">🔥</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{breakouts.filter(b => b.signal === "STRONG").length}</div>
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
              {/* Starters */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  🔥 Must Start ({dailyLineup.starters.length})
                </h3>
                <div className="space-y-2">
                  {dailyLineup.starters.map((player, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-center gap-3 flex-1">
                        <Badge className={getConfidenceColor(player.confidence)}>
                          {player.confidence}
                        </Badge>
                        <div className="flex-1">
                          <div className="font-semibold">{player.player}</div>
                          <div className="text-sm text-muted-foreground">{player.position} • {player.opponent}</div>
                        </div>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <Badge variant="outline">{player.matchup}</Badge>
                        <Badge variant="outline">{player.parkFactor}</Badge>
                        <Badge variant="outline">{player.platoon}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bench */}
              <div>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  ⚠️ Consider Benching ({dailyLineup.bench.length})
                </h3>
                <div className="space-y-2">
                  {dailyLineup.bench.map((player, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-center gap-3 flex-1">
                        <Badge className={getConfidenceColor(player.confidence)}>
                          {player.confidence}
                        </Badge>
                        <div className="flex-1">
                          <div className="font-semibold">{player.player}</div>
                          <div className="text-sm text-muted-foreground">{player.position} • {player.opponent}</div>
                        </div>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <Badge variant="outline">{player.matchup}</Badge>
                        <Badge variant="outline">{player.parkFactor}</Badge>
                        <Badge variant="outline">{player.platoon}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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

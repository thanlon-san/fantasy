import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export default function Home() {
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
              <CardTitle className="text-sm font-medium">Roster</CardTitle>
              <span className="text-2xl">👥</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">24</div>
              <p className="text-xs text-muted-foreground">Active players</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Breakouts</CardTitle>
              <span className="text-2xl">🔥</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3</div>
              <p className="text-xs text-muted-foreground">STRONG signals</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <span className="text-2xl">🏆</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">72%</div>
              <p className="text-xs text-muted-foreground">Season performance</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Tools Grid */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Daily Lineup */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">📊</span>
                <div>
                  <CardTitle>Daily Lineup</CardTitle>
                  <CardDescription>Start/sit recommendations</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800">
                  <span className="font-medium text-sm">🔥 Must Start</span>
                  <Badge className="bg-green-600">6 players</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800">
                  <span className="font-medium text-sm">⚠️ Consider Benching</span>
                  <Badge variant="secondary">2 players</Badge>
                </div>
              </div>
              <Button className="w-full" size="lg">
                View Full Lineup
              </Button>
            </CardContent>
          </Card>

          {/* Waiver Wire */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">🎯</span>
                <div>
                  <CardTitle>Waiver Wire</CardTitle>
                  <CardDescription>Value pickups available</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800">
                  <span className="font-medium text-sm">✅ Strong Pickups</span>
                  <Badge className="bg-purple-600">8 available</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
                  <span className="font-medium text-sm">💎 Keeper Value</span>
                  <Badge className="bg-blue-600">3 gems</Badge>
                </div>
              </div>
              <Button className="w-full" size="lg" variant="outline">
                Browse Waivers
              </Button>
            </CardContent>
          </Card>

          {/* Breakout Detector */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">🔬</span>
                <div>
                  <CardTitle>Breakout Detector</CardTitle>
                  <CardDescription>Statcast-powered analysis</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800">
                  <span className="font-medium text-sm">🔥 STRONG</span>
                  <Badge className="bg-orange-600">3 players</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800">
                  <span className="font-medium text-sm">⚡ EMERGING</span>
                  <Badge className="bg-amber-600">5 players</Badge>
                </div>
              </div>
              <Button className="w-full" size="lg" variant="outline">
                Scan Free Agents
              </Button>
            </CardContent>
          </Card>

          {/* Keeper Analyzer */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-2">
                <span className="text-3xl">⭐</span>
                <div>
                  <CardTitle>Keeper Analyzer</CardTitle>
                  <CardDescription>Optimize your keepers</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800">
                  <span className="font-medium text-sm">💰 Top Value</span>
                  <Badge className="bg-emerald-600">Betts (R1)</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-sky-50 dark:bg-sky-950 border border-sky-200 dark:border-sky-800">
                  <span className="font-medium text-sm">📈 Surplus</span>
                  <Badge className="bg-sky-600">+427 ADP</Badge>
                </div>
              </div>
              <Button className="w-full" size="lg" variant="outline">
                Analyze Keepers
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-muted-foreground">
          <p>Built with Next.js • Powered by Statcast • Deployed on Vercel</p>
          <p className="mt-1">🏆 Your year-round competitive advantage</p>
        </footer>
      </div>
    </main>
  )
}

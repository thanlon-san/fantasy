import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"

export default function LineupPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-6">
          <Link href="/">
            <Button variant="outline">← Back to Dashboard</Button>
          </Link>
        </div>

        <header className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            📊 Daily Lineup Optimizer
          </h1>
          <p className="text-muted-foreground text-lg">
            Start/sit recommendations based on matchups, park factors, and more
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-green-600">🔥 Must Start (6)</CardTitle>
              <CardDescription>Players with favorable matchups today</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: "Shohei Ohtani", matchup: "vs. COL", score: 95, reason: "Great park, weak pitcher" },
                { name: "Ronald Acuña Jr.", matchup: "vs. MIA", score: 92, reason: "Hot streak, platoon advantage" },
                { name: "Mookie Betts", matchup: "@ SF", score: 90, reason: "Strong recent form" },
                { name: "Juan Soto", matchup: "vs. ARI", score: 88, reason: "Favorable matchup" },
                { name: "Aaron Judge", matchup: "@ BAL", score: 85, reason: "Breakout signal detected" },
                { name: "Freddie Freeman", matchup: "@ SF", score: 83, reason: "Consistent performer" },
              ].map((player) => (
                <div key={player.name} className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                  <div>
                    <div className="font-semibold">{player.name}</div>
                    <div className="text-sm text-muted-foreground">{player.reason}</div>
                  </div>
                  <div className="text-right">
                    <Badge className="bg-green-600 mb-1">{player.score}</Badge>
                    <div className="text-xs text-muted-foreground">{player.matchup}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-yellow-600">⚠️ Consider Benching (2)</CardTitle>
              <CardDescription>Players with tough matchups today</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: "Pete Alonso", matchup: "@ LAD", score: 42, reason: "vs. ace pitcher, cold streak" },
                { name: "Kyle Tucker", matchup: "vs. CLE", score: 38, reason: "Platoon disadvantage" },
              ].map((player) => (
                <div key={player.name} className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <div>
                    <div className="font-semibold">{player.name}</div>
                    <div className="text-sm text-muted-foreground">{player.reason}</div>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" className="mb-1">{player.score}</Badge>
                    <div className="text-xs text-muted-foreground">{player.matchup}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
            <CardDescription>Multi-factor lineup optimization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="font-semibold mb-2">📊 Scoring Factors</h3>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• 30% Matchup (pitcher quality, splits)</li>
                  <li>• 25% Recent Form (last 7-14 days)</li>
                  <li>• 20% Park Factor (hitter-friendly venues)</li>
                  <li>• 15% Platoon Advantage (L vs R, R vs L)</li>
                  <li>• 10% Breakout Signals (Statcast data)</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold mb-2">🚀 To Use This Tool</h3>
                <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-lg text-sm font-mono">
                  <p className="mb-2">From your terminal:</p>
                  <code className="text-xs">cd apps/keeper-advisor<br/>npm run lineup</code>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

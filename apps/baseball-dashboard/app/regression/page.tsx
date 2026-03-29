"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import {
  ArrowLeft, TrendingDown, TrendingUp, BarChart3, RefreshCw,
} from "lucide-react"
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, ReferenceLine, ZAxis,
} from "recharts"

import type { RegressionCandidate } from "@fantasy/types"
import { RegressionCandidateSchema } from "@fantasy/types"
import { z } from "zod"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type Candidate = RegressionCandidate

const RegressionDataSchema = z.object({
  buy_low: z.array(RegressionCandidateSchema),
  sell_high: z.array(RegressionCandidateSchema),
  scanned: z.number(),
  generated_at: z.string(),
})

type RegressionData = z.infer<typeof RegressionDataSchema>

function stat(v: number | null | undefined, digits = 3): string {
  if (v == null) return "—"
  return v.toFixed(digits)
}

function DeltaBadge({ delta, invert }: { delta: number | null | undefined; invert?: boolean }) {
  if (delta == null) return null
  const positive = invert ? delta < 0 : delta > 0
  return (
    <Badge
      variant="outline"
      className={`text-xs font-mono tabular-nums ${
        positive
          ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
          : "border-rose-500/40 text-rose-400 bg-rose-500/10"
      }`}
    >
      {delta > 0 ? "+" : ""}
      {delta.toFixed(3)}
    </Badge>
  )
}

function RegressionScatter({ buyLow, sellHigh }: { buyLow: Candidate[]; sellHigh: Candidate[] }) {
  const hitters = [...buyLow, ...sellHigh].filter(c => c.player_type === "hitter" && c.ba != null && c.xba != null)
  if (hitters.length === 0) return null

  const buyData = hitters
    .filter(c => c.direction === "BUY_LOW")
    .map(c => ({ x: c.xba!, y: c.ba!, name: c.name, confidence: c.confidence }))
  const sellData = hitters
    .filter(c => c.direction === "SELL_HIGH")
    .map(c => ({ x: c.xba!, y: c.ba!, name: c.name, confidence: c.confidence }))

  const allX = hitters.map(c => c.xba!)
  const allY = hitters.map(c => c.ba!)
  const min = Math.min(...allX, ...allY) - 0.015
  const max = Math.max(...allX, ...allY) + 0.015

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4 mb-8">
      <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
        Actual BA vs Expected BA — players far from the diagonal are mispriced
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
          <XAxis
            type="number" dataKey="x" name="xBA" domain={[min, max]}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            label={{ value: "Expected BA (xBA)", position: "bottom", offset: 0, style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" } }}
            tickFormatter={(v: number) => v.toFixed(3)}
          />
          <YAxis
            type="number" dataKey="y" name="BA" domain={[min, max]}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            label={{ value: "Actual BA", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" } }}
            tickFormatter={(v: number) => v.toFixed(3)}
          />
          <ZAxis type="number" dataKey="confidence" range={[40, 200]} />
          <RechartsTooltip
            content={({ payload }) => {
              if (!payload?.length) return null
              const d = payload[0].payload
              return (
                <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
                  <div className="font-semibold">{d.name}</div>
                  <div className="text-muted-foreground">
                    BA: {d.y.toFixed(3)} · xBA: {d.x.toFixed(3)}
                  </div>
                </div>
              )
            }}
          />
          <ReferenceLine
            segment={[{ x: min, y: min }, { x: max, y: max }]}
            stroke="hsl(var(--muted-foreground))" strokeDasharray="6 3" opacity={0.5}
          />
          <Scatter name="Buy Low" data={buyData} fill="#10b981" opacity={0.8} />
          <Scatter name="Sell High" data={sellData} fill="#f43f5e" opacity={0.8} />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex items-center justify-center gap-6 mt-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Buy Low (below line)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Sell High (above line)</span>
      </div>
    </div>
  )
}

function CandidateTable({ candidates, type }: { candidates: Candidate[]; type: "buy_low" | "sell_high" }) {
  const isBuyLow = type === "buy_low"
  const hitters = candidates.filter(c => c.player_type === "hitter")
  const pitchers = candidates.filter(c => c.player_type === "pitcher")

  if (candidates.length === 0) {
    return (
      <div className="rounded-md border bg-card p-8 text-center text-muted-foreground">
        No {isBuyLow ? "buy-low" : "sell-high"} candidates found
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {hitters.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Hitters ({hitters.length})
          </h3>
          <div className="rounded-md border bg-card shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 text-xs">
                  <TableHead>Player</TableHead>
                  <TableHead className="text-right">BA</TableHead>
                  <TableHead className="text-right">xBA</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                  <TableHead className="text-right">SLG</TableHead>
                  <TableHead className="text-right">xSLG</TableHead>
                  <TableHead className="text-right hidden sm:table-cell">xwOBA</TableHead>
                  <TableHead className="text-right">Conf</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hitters.map((c, i) => (
                  <TableRow key={i} className="hover:bg-muted/40">
                    <TableCell>
                      <Link href={`/player/${encodeURIComponent(c.name)}`} className="hover:underline">
                        <div className="flex flex-col leading-tight">
                          <span className="font-semibold text-sm">{c.name}</span>
                          <span className="text-xs text-muted-foreground">{c.position} · {c.team}</span>
                        </div>
                      </Link>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">{stat(c.ba)}</TableCell>
                    <TableCell className="text-right font-mono text-sm font-semibold">{stat(c.xba)}</TableCell>
                    <TableCell className="text-right"><DeltaBadge delta={c.ba_delta} /></TableCell>
                    <TableCell className="text-right font-mono text-sm">{stat(c.slg)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{stat(c.xslg)}</TableCell>
                    <TableCell className="text-right font-mono text-sm hidden sm:table-cell">{stat(c.xwoba)}</TableCell>
                    <TableCell className="text-right">
                      <Badge className={`text-xs w-10 justify-center font-bold tabular-nums ${
                        c.confidence >= 70 ? "bg-emerald-600 text-white" : c.confidence >= 50 ? "bg-amber-600 text-white" : "bg-slate-600 text-white"
                      }`}>
                        {Math.round(c.confidence)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {pitchers.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Pitchers ({pitchers.length})
          </h3>
          <div className="rounded-md border bg-card shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 text-xs">
                  <TableHead>Player</TableHead>
                  <TableHead className="text-right">FIP</TableHead>
                  <TableHead className="text-right">xERA</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                  <TableHead className="text-right hidden sm:table-cell">xwOBA Ag.</TableHead>
                  <TableHead className="text-right">Conf</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pitchers.map((c, i) => (
                  <TableRow key={i} className="hover:bg-muted/40">
                    <TableCell>
                      <Link href={`/player/${encodeURIComponent(c.name)}`} className="hover:underline">
                        <div className="flex flex-col leading-tight">
                          <span className="font-semibold text-sm">{c.name}</span>
                          <span className="text-xs text-muted-foreground">{c.position} · {c.team}</span>
                        </div>
                      </Link>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm font-semibold">{stat(c.fip, 2)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{stat(c.xera, 2)}</TableCell>
                    <TableCell className="text-right"><DeltaBadge delta={c.era_fip_delta} invert /></TableCell>
                    <TableCell className="text-right font-mono text-sm hidden sm:table-cell">{stat(c.xwoba)}</TableCell>
                    <TableCell className="text-right">
                      <Badge className={`text-xs w-10 justify-center font-bold tabular-nums ${
                        c.confidence >= 70 ? "bg-emerald-600 text-white" : c.confidence >= 50 ? "bg-amber-600 text-white" : "bg-slate-600 text-white"
                      }`}>
                        {Math.round(c.confidence)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  )
}

export default function RegressionPage() {
  const { data, isLoading, error, refetch } = useQuery<RegressionData>({
    queryKey: ["regression"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/regression`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      return RegressionDataSchema.parse(await res.json())
    },
  })

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
          </div>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                <BarChart3 className="h-7 w-7 text-primary" />
                Regression Candidates
              </h1>
              <p className="text-muted-foreground text-sm mt-1">
                Players whose actual stats diverge from expected stats — the market is mispricing them
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading} className="gap-1.5">
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            {error instanceof Error ? error.message : "Failed to fetch"}. Make sure the draft server is running (port 8001).
          </div>
        )}

        {isLoading && !data ? (
          <div className="space-y-4">
            {[1, 2].map(i => (
              <div key={i} className="h-48 rounded-lg border bg-card animate-pulse" />
            ))}
          </div>
        ) : data ? (
          <div className="space-y-8">
            <RegressionScatter buyLow={data.buy_low} sellHigh={data.sell_high} />

            <section>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-5 w-5 text-emerald-500" />
                <h2 className="text-lg font-bold">Buy Low</h2>
                <Badge variant="secondary">{data.buy_low.length}</Badge>
                <span className="text-xs text-muted-foreground ml-1">
                  xBA &gt; BA by 30+ points — contact quality is elite, results haven&apos;t caught up
                </span>
              </div>
              <CandidateTable candidates={data.buy_low} type="buy_low" />
            </section>

            <section>
              <div className="flex items-center gap-2 mb-3">
                <TrendingDown className="h-5 w-5 text-rose-500" />
                <h2 className="text-lg font-bold">Sell High</h2>
                <Badge variant="secondary">{data.sell_high.length}</Badge>
                <span className="text-xs text-muted-foreground ml-1">
                  BA &gt; xBA by 30+ points — over-performing contact quality, regression incoming
                </span>
              </div>
              <CandidateTable candidates={data.sell_high} type="sell_high" />
            </section>

            <footer className="text-center text-xs text-muted-foreground pt-4 border-t">
              Scanned {data.scanned} players · Data from Baseball Savant xStats
              {data.generated_at && (
                <span> · Updated {new Date(data.generated_at).toLocaleTimeString()}</span>
              )}
            </footer>
          </div>
        ) : null}
      </div>
    </main>
  )
}

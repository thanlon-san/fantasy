"use client"

import { Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { ArrowLeft, RefreshCw, User, AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react"
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer,   BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip,
} from "recharts"

import type { PlayerProfile } from "@fantasy/types"
import { PlayerProfileSchema } from "@fantasy/types"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

function statFmt(v: number | null | undefined, digits = 3): string {
  if (v == null) return "—"
  return v.toFixed(digits)
}

function percentile(value: number | undefined | null, isInverse = false): number {
  if (value == null) return 50
  if (isInverse) return Math.max(0, Math.min(100, 100 - value * 10))
  return Math.max(0, Math.min(100, value))
}

function HitterRadar({ proj }: { proj: NonNullable<PlayerProfile["projection"]> }) {
  const data = [
    { metric: "Power", value: percentile(proj.hr, false), fullMark: 100, raw: `${proj.hr ?? "—"} HR` },
    { metric: "Speed", value: percentile(proj.sb, false), fullMark: 100, raw: `${proj.sb ?? "—"} SB` },
    { metric: "Contact", value: proj.avg ? Math.round(proj.avg * 333) : 50, fullMark: 100, raw: `.${Math.round((proj.avg ?? 0) * 1000)} AVG` },
    { metric: "OPS", value: proj.ops ? Math.round(proj.ops * 100) : 50, fullMark: 100, raw: `${statFmt(proj.ops)} OPS` },
    { metric: "wRC+", value: percentile(proj.wrc_plus), fullMark: 100, raw: `${proj.wrc_plus ?? "—"} wRC+` },
    { metric: "Volume", value: proj.pa ? Math.round(Math.min(100, (proj.pa / 600) * 100)) : 50, fullMark: 100, raw: `${proj.pa ?? "—"} PA` },
  ]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="hsl(var(--border))" opacity={0.5} />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
        />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <RechartsTooltip
          content={({ payload }) => {
            if (!payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="rounded-md border bg-popover px-3 py-1.5 text-xs shadow-md">
                <div className="font-semibold">{d.metric}</div>
                <div className="text-muted-foreground">{d.raw}</div>
              </div>
            )
          }}
        />
        <Radar dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

function PitcherRadar({ proj }: { proj: NonNullable<PlayerProfile["projection"]> }) {
  const data = [
    { metric: "K", value: proj.k ? Math.round(Math.min(100, (proj.k / 220) * 100)) : 50, fullMark: 100, raw: `${proj.k ?? "—"} K` },
    { metric: "ERA", value: proj.era ? Math.round(Math.max(0, 100 - (proj.era - 2.0) * 20)) : 50, fullMark: 100, raw: `${statFmt(proj.era, 2)} ERA` },
    { metric: "WHIP", value: proj.whip ? Math.round(Math.max(0, 100 - (proj.whip - 0.9) * 150)) : 50, fullMark: 100, raw: `${statFmt(proj.whip, 2)} WHIP` },
    { metric: "FIP", value: proj.fip ? Math.round(Math.max(0, 100 - (proj.fip - 2.0) * 20)) : 50, fullMark: 100, raw: `${statFmt(proj.fip, 2)} FIP` },
    { metric: "K-BB%", value: percentile(proj.k_bb_pct), fullMark: 100, raw: `${statFmt(proj.k_bb_pct, 1)}% K-BB%` },
    { metric: "Volume", value: proj.ip ? Math.round(Math.min(100, (proj.ip / 200) * 100)) : 50, fullMark: 100, raw: `${statFmt(proj.ip, 1)} IP` },
  ]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="hsl(var(--border))" opacity={0.5} />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
        />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <RechartsTooltip
          content={({ payload }) => {
            if (!payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="rounded-md border bg-popover px-3 py-1.5 text-xs shadow-md">
                <div className="font-semibold">{d.metric}</div>
                <div className="text-muted-foreground">{d.raw}</div>
              </div>
            )
          }}
        />
        <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

function RollingStatsChart({ stats }: { stats: NonNullable<PlayerProfile["recent_stats"]> }) {
  const windows = ["last_7_days", "last_14_days", "last_30_days"] as const
  const labels = ["7d", "14d", "30d"]
  const isHitter = stats.last_7_days?.avg != null || stats.last_14_days?.avg != null

  if (isHitter) {
    const chartData = windows.map((w, i) => ({
      window: labels[i],
      AVG: stats[w]?.avg != null ? Math.round((stats[w]?.avg ?? 0) * 1000) : null,
      OPS: stats[w]?.ops != null ? Math.round((stats[w]?.ops ?? 0) * 1000) : null,
      HR: stats[w]?.hr ?? null,
    })).filter(d => d.AVG != null || d.OPS != null)

    if (chartData.length === 0) return null

    return (
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Rolling Stats</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} vertical={false} />
            <XAxis dataKey="window" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
            <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
            <RechartsTooltip
              content={({ payload, label }) => {
                if (!payload?.length) return null
                return (
                  <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
                    <div className="font-semibold mb-1">{label}</div>
                    {payload.map((p, i) => (
                      <div key={i} className="text-muted-foreground">
                        {p.name}: {p.name === "HR" ? p.value : `.${p.value}`}
                      </div>
                    ))}
                  </div>
                )
              }}
            />
            <Bar dataKey="AVG" fill="#10b981" opacity={0.7} radius={[3, 3, 0, 0]} name="AVG (×1000)" />
            <Bar dataKey="OPS" fill="#6366f1" opacity={0.7} radius={[3, 3, 0, 0]} name="OPS (×1000)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const chartData = windows.map((w, i) => ({
    window: labels[i],
    ERA: stats[w]?.era ?? null,
    WHIP: stats[w]?.whip != null ? Math.round((stats[w]?.whip ?? 0) * 100) / 100 : null,
    K: stats[w]?.k ?? null,
  })).filter(d => d.ERA != null || d.K != null)

  if (chartData.length === 0) return null

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Rolling Stats</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} vertical={false} />
          <XAxis dataKey="window" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
          <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
          <RechartsTooltip
            content={({ payload, label }) => {
              if (!payload?.length) return null
              return (
                <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
                  <div className="font-semibold mb-1">{label}</div>
                  {payload.map((p, i) => (
                    <div key={i} className="text-muted-foreground">{p.name}: {p.value}</div>
                  ))}
                </div>
              )
            }}
          />
          <Bar dataKey="K" fill="#f59e0b" opacity={0.7} radius={[3, 3, 0, 0]} name="K" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function XStatsComparison({ reg }: { reg: NonNullable<PlayerProfile["regression"]> }) {
  const isHitter = reg.ba != null || reg.xba != null

  if (isHitter) {
    const data = [
      { metric: "BA", actual: reg.ba, expected: reg.xba },
      { metric: "SLG", actual: reg.slg, expected: reg.xslg },
    ].filter(d => d.actual != null || d.expected != null)

    if (data.length === 0) return null

    const chartData = data.map(d => ({
      metric: d.metric,
      Actual: d.actual != null ? Math.round(d.actual * 1000) : 0,
      Expected: d.expected != null ? Math.round(d.expected * 1000) : 0,
    }))

    return (
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Actual vs Expected (xStats)
        </h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} vertical={false} />
            <XAxis dataKey="metric" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
            <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
            <RechartsTooltip
              content={({ payload, label }) => {
                if (!payload?.length) return null
                return (
                  <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
                    <div className="font-semibold mb-1">{label}</div>
                    {payload.map((p, i) => (
                      <div key={i} className="text-muted-foreground">{p.name}: .{p.value}</div>
                    ))}
                  </div>
                )
              }}
            />
            <Bar dataKey="Actual" fill="#f43f5e" opacity={0.7} radius={[3, 3, 0, 0]} />
            <Bar dataKey="Expected" fill="#10b981" opacity={0.7} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" />Actual</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />Expected</span>
        </div>
      </div>
    )
  }

  return null
}

function RecentStatsTable({ stats, isHitter }: { stats: NonNullable<PlayerProfile["recent_stats"]>; isHitter: boolean }) {
  const windows = [
    { key: "last_7_days", label: "7d" },
    { key: "last_14_days", label: "14d" },
    { key: "last_30_days", label: "30d" },
  ]

  const metrics = isHitter
    ? [
        { key: "avg", label: "AVG", fmt: (v: number) => v.toFixed(3) },
        { key: "ops", label: "OPS", fmt: (v: number) => v.toFixed(3) },
        { key: "hr", label: "HR", fmt: (v: number) => String(Math.round(v)) },
        { key: "rbi", label: "RBI", fmt: (v: number) => String(Math.round(v)) },
        { key: "sb", label: "SB", fmt: (v: number) => String(Math.round(v)) },
        { key: "r", label: "R", fmt: (v: number) => String(Math.round(v)) },
        { key: "bb", label: "BB", fmt: (v: number) => String(Math.round(v)) },
      ]
    : [
        { key: "era", label: "ERA", fmt: (v: number) => v.toFixed(2) },
        { key: "whip", label: "WHIP", fmt: (v: number) => v.toFixed(2) },
        { key: "k", label: "K", fmt: (v: number) => String(Math.round(v)) },
        { key: "ip", label: "IP", fmt: (v: number) => v.toFixed(1) },
        { key: "sv", label: "SV", fmt: (v: number) => String(Math.round(v)) },
        { key: "qs", label: "QS", fmt: (v: number) => String(Math.round(v)) },
      ]

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Recent Performance</h3>
      <div className="rounded-md border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 text-xs">
              <TableHead>Metric</TableHead>
              {windows.map(w => (
                <TableHead key={w.key} className="text-right">{w.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {metrics.map(m => (
              <TableRow key={m.key} className="hover:bg-muted/40">
                <TableCell className="font-medium text-sm">{m.label}</TableCell>
                {windows.map(w => {
                  const val = stats[w.key]?.[m.key]
                  return (
                    <TableCell key={w.key} className="text-right font-mono text-sm tabular-nums">
                      {val != null ? m.fmt(val) : "—"}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function pctileColor(pct: number | null | undefined): string {
  if (pct == null) return "bg-slate-700"
  if (pct >= 90) return "bg-red-600"
  if (pct >= 75) return "bg-orange-500"
  if (pct >= 50) return "bg-amber-400"
  if (pct >= 25) return "bg-sky-400"
  return "bg-blue-600"
}

function pctileTextColor(pct: number | null | undefined): string {
  if (pct == null) return "text-slate-500"
  if (pct >= 90) return "text-red-400"
  if (pct >= 75) return "text-orange-400"
  if (pct >= 50) return "text-amber-300"
  if (pct >= 25) return "text-sky-400"
  return "text-blue-400"
}

function SavantPercentileCard({ pctiles, isPitcher }: {
  pctiles: NonNullable<PlayerProfile["savant_percentiles"]>
  isPitcher: boolean
}) {
  const metrics = isPitcher
    ? [
        { key: "fastball_velo", label: "Fastball Velo" },
        { key: "whiff_pct", label: "Whiff%" },
        { key: "k_pct", label: "K%" },
        { key: "bb_pct", label: "BB%" },
        { key: "exit_velocity", label: "Exit Velo (against)" },
        { key: "hard_hit_pct", label: "Hard Hit% (against)" },
        { key: "barrel_pct", label: "Barrel% (against)" },
        { key: "xba", label: "xBA (against)" },
        { key: "xslg", label: "xSLG (against)" },
        { key: "xwoba", label: "xwOBA (against)" },
        { key: "xera", label: "xERA" },
      ]
    : [
        { key: "exit_velocity", label: "Exit Velocity" },
        { key: "hard_hit_pct", label: "Hard Hit%" },
        { key: "barrel_pct", label: "Barrel%" },
        { key: "xba", label: "xBA" },
        { key: "xslg", label: "xSLG" },
        { key: "xwoba", label: "xwOBA" },
        { key: "sprint_speed", label: "Sprint Speed" },
        { key: "chase_rate", label: "Chase Rate" },
        { key: "whiff_pct", label: "Whiff%" },
        { key: "k_pct", label: "K%" },
        { key: "bb_pct", label: "BB%" },
      ]

  const validMetrics = metrics.filter(m => {
    const val = pctiles[m.key as keyof typeof pctiles]
    return val != null
  })

  if (validMetrics.length === 0) return null

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Statcast Percentile Rankings
        </h3>
        {isPitcher && pctiles.stuff_plus != null && (
          <Badge variant="outline" className={`text-xs font-bold ${
            pctiles.stuff_plus >= 110 ? "border-red-500/40 text-red-400" :
            pctiles.stuff_plus >= 100 ? "border-amber-500/40 text-amber-400" :
            "border-sky-500/40 text-sky-400"
          }`}>
            Stuff+ {pctiles.stuff_plus}
          </Badge>
        )}
      </div>
      <div className="space-y-2">
        {validMetrics.map(m => {
          const val = pctiles[m.key as keyof typeof pctiles] as number
          return (
            <div key={m.key} className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0 text-right">{m.label}</span>
              <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden relative">
                <div
                  className={`h-full rounded-full transition-all ${pctileColor(val)}`}
                  style={{ width: `${Math.max(3, val)}%` }}
                />
              </div>
              <span className={`text-xs font-bold tabular-nums w-8 text-right ${pctileTextColor(val)}`}>
                {val}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-600" />Poor</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-400" />Below Avg</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />Average</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" />Great</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-600" />Elite</span>
      </div>
    </div>
  )
}

function PlayerProfileInner() {
  const searchParams = useSearchParams()
  const playerName = searchParams.get("name") ?? ""

  const { data: profile, isLoading, error, refetch } = useQuery<PlayerProfile>({
    queryKey: ["player-profile", playerName],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/season/player-profile?name=${encodeURIComponent(playerName)}`,
        { cache: "no-store" }
      )
      if (!res.ok) throw new Error(`API ${res.status}`)
      return PlayerProfileSchema.parse(await res.json())
    },
    enabled: !!playerName,
    refetchInterval: 300_000,
  })

  const isPitcher = profile?.projection?.type === "pitcher"

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <header className="mb-6">
          <div className="flex items-center gap-3 mb-3">
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="ml-auto gap-1.5 text-muted-foreground">
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
                <User className="h-7 w-7 text-slate-300" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight">{playerName}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                  {profile?.team && (
                    <span className="text-sm text-muted-foreground">{profile.team}</span>
                  )}
                  {profile?.position && (
                    <Badge variant="outline" className="text-xs">{profile.position}</Badge>
                  )}
                  {profile?.injury && (
                    <Badge variant="destructive" className="text-xs gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {profile.injury.badge}
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {profile?.projection?.ros_value != null && (
              <div className="ml-auto text-right">
                <div className="text-3xl font-bold tabular-nums text-emerald-500">
                  {profile.projection.ros_value}
                </div>
                <div className="text-xs text-muted-foreground">ROS Value</div>
              </div>
            )}
          </div>

          {profile?.injury && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
              <span className="text-red-300">{profile.injury.description} ({profile.injury.date})</span>
            </div>
          )}
        </header>

        {isLoading && !profile && (
          <div className="text-center py-16 text-muted-foreground">
            <RefreshCw className="h-8 w-8 mx-auto mb-3 animate-spin opacity-40" />
            <p>Loading player profile...</p>
          </div>
        )}

        {error && !isLoading && (
          <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed">
            <p className="font-medium">{error instanceof Error ? error.message : "Failed to load"}</p>
            <p className="text-xs mt-1">Make sure the season server is running on port 8001</p>
          </div>
        )}

        {profile && !profile.found && !isLoading && (
          <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed">
            <User className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No data found for &quot;{playerName}&quot;</p>
            <p className="text-xs mt-1">Projection and stats data may not be available for this player</p>
          </div>
        )}

        {profile && profile.found && (
          <div className="space-y-8">
            {/* Top row: Radar + Projection table */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Radar Chart */}
              {profile.projection && (
                <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    ROS Projection Profile
                  </h3>
                  {isPitcher
                    ? <PitcherRadar proj={profile.projection} />
                    : <HitterRadar proj={profile.projection} />
                  }
                </div>
              )}

              {/* Projection Table */}
              {profile.projection && (
                <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    Steamer ROS Projections
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {isPitcher ? (
                      <>
                        {[
                          { label: "IP", value: statFmt(profile.projection.ip, 1) },
                          { label: "ERA", value: statFmt(profile.projection.era, 2), color: (profile.projection.era ?? 5) <= 3.2 ? "text-emerald-400" : (profile.projection.era ?? 5) <= 4.0 ? "text-amber-400" : "text-rose-400" },
                          { label: "WHIP", value: statFmt(profile.projection.whip, 2) },
                          { label: "K", value: String(profile.projection.k ?? "—") },
                          { label: "QS", value: String(profile.projection.qs ?? "—") },
                          { label: "FIP", value: statFmt(profile.projection.fip, 2) },
                          { label: "K-BB%", value: `${statFmt(profile.projection.k_bb_pct, 1)}%` },
                          { label: "WAR", value: statFmt(profile.projection.war, 1) },
                          { label: "Value", value: String(profile.projection.ros_value ?? "—"), color: "text-emerald-400 font-bold" },
                        ].map(s => (
                          <div key={s.label} className="bg-muted/30 rounded-lg p-3 text-center">
                            <div className="text-[10px] text-muted-foreground uppercase mb-1">{s.label}</div>
                            <div className={`text-lg font-bold tabular-nums ${s.color ?? ""}`}>{s.value}</div>
                          </div>
                        ))}
                      </>
                    ) : (
                      <>
                        {[
                          { label: "PA", value: String(profile.projection.pa ?? "—") },
                          { label: "AVG", value: statFmt(profile.projection.avg) },
                          { label: "HR", value: String(profile.projection.hr ?? "—") },
                          { label: "RBI", value: String(profile.projection.rbi ?? "—") },
                          { label: "SB", value: String(profile.projection.sb ?? "—") },
                          { label: "OPS", value: statFmt(profile.projection.ops) },
                          { label: "wRC+", value: String(profile.projection.wrc_plus ?? "—"), color: (profile.projection.wrc_plus ?? 0) >= 120 ? "text-emerald-400" : (profile.projection.wrc_plus ?? 0) >= 100 ? "text-amber-400" : "text-rose-400" },
                          { label: "WAR", value: statFmt(profile.projection.war, 1) },
                          { label: "Value", value: String(profile.projection.ros_value ?? "—"), color: "text-emerald-400 font-bold" },
                        ].map(s => (
                          <div key={s.label} className="bg-muted/30 rounded-lg p-3 text-center">
                            <div className="text-[10px] text-muted-foreground uppercase mb-1">{s.label}</div>
                            <div className={`text-lg font-bold tabular-nums ${s.color ?? ""}`}>{s.value}</div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Regression Analysis */}
            {profile.regression && (
              <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Regression Analysis
                  </h3>
                  <Badge
                    variant="outline"
                    className={`text-xs ${
                      profile.regression.direction === "BUY_LOW"
                        ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
                        : profile.regression.direction === "SELL_HIGH"
                        ? "border-rose-500/40 text-rose-400 bg-rose-500/10"
                        : "border-slate-500/40 text-slate-400"
                    }`}
                  >
                    {profile.regression.direction === "BUY_LOW" && <TrendingUp className="h-3 w-3 mr-1" />}
                    {profile.regression.direction === "SELL_HIGH" && <TrendingDown className="h-3 w-3 mr-1" />}
                    {profile.regression.direction === "NEUTRAL" && <Minus className="h-3 w-3 mr-1" />}
                    {profile.regression.direction} · {Math.round(profile.regression.confidence)}% conf
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-4">{profile.regression.summary}</p>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <XStatsComparison reg={profile.regression} />

                  {profile.regression.improving_metrics.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground mb-2">Improving Metrics</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {profile.regression.improving_metrics.map((m, i) => (
                          <Badge key={i} variant="outline" className="text-xs border-emerald-500/30 text-emerald-400">{m}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Savant Percentile Rankings */}
            {profile.savant_percentiles && (
              <SavantPercentileCard
                pctiles={profile.savant_percentiles}
                isPitcher={isPitcher}
              />
            )}

            {/* Recent Stats */}
            {profile.recent_stats && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <RecentStatsTable stats={profile.recent_stats} isHitter={!isPitcher} />
                <RollingStatsChart stats={profile.recent_stats} />
              </div>
            )}

            <footer className="text-center text-xs text-muted-foreground pt-4 border-t">
              Profile data combines Steamer ROS projections, Baseball Savant xStats, and recent game logs
              {profile.generated_at && (
                <span> · Updated {new Date(profile.generated_at).toLocaleTimeString()}</span>
              )}
            </footer>
          </div>
        )}
      </div>
    </main>
  )
}

export default function PlayerProfilePage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="container mx-auto px-4 py-8 max-w-5xl text-center text-muted-foreground">Loading player...</div>
      </main>
    }>
      <PlayerProfileInner />
    </Suspense>
  )
}

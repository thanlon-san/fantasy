"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, RefreshCw, Users, DollarSign } from "lucide-react"

import { HitterProjectionSchema, PitcherProjectionSchema } from "@fantasy/types"
import { z } from "zod"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

const ProjectionDataSchema = z.object({
  hitters: z.array(HitterProjectionSchema),
  pitchers: z.array(PitcherProjectionSchema),
  total_scanned: z.number(),
  generated_at: z.string(),
})

type ProjectionData = z.infer<typeof ProjectionDataSchema>

function sourceBadge(src: string) {
  if (src === "roster") return <Badge variant="outline" className="text-[10px] px-1 py-0 border-emerald-500/40 text-emerald-400">Roster</Badge>
  return <Badge variant="outline" className="text-[10px] px-1 py-0 border-amber-500/40 text-amber-400">FA</Badge>
}

function valueBadge(val: number) {
  if (val >= 80) return "bg-emerald-600 text-white"
  if (val >= 40) return "bg-amber-600 text-white"
  return "bg-slate-600 text-white"
}

export default function ProjectionsPage() {
  const { data, isLoading, error, refetch } = useQuery<ProjectionData>({
    queryKey: ["projections"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/season/projections`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      return ProjectionDataSchema.parse(await res.json())
    },
  })

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <header className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <DollarSign className="h-6 w-6 text-emerald-500" />
              ROS Projections
            </h1>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="ml-auto gap-1.5 text-muted-foreground">
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
          <p className="text-sm text-muted-foreground ml-11">
            Steamer rest-of-season projections via FanGraphs — your roster vs. top free agents
          </p>
        </header>

        {isLoading && !data && (
          <div className="text-center py-16 text-muted-foreground">
            <RefreshCw className="h-8 w-8 mx-auto mb-3 animate-spin opacity-40" />
            <p>Loading projections from draft server...</p>
            <p className="text-xs mt-1">Ensure <code>draft_server.py</code> is running on port 8001</p>
          </div>
        )}

        {error && !isLoading && (
          <div className="text-center py-16 text-muted-foreground border rounded-lg border-dashed">
            <Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">{error instanceof Error ? error.message : "Failed to load"}</p>
            <p className="text-xs mt-1">Make sure the season server is running</p>
          </div>
        )}

        {data && (
          <Tabs defaultValue="hitters">
            <TabsList className="mb-4">
              <TabsTrigger value="hitters">Hitters ({data.hitters.length})</TabsTrigger>
              <TabsTrigger value="pitchers">Pitchers ({data.pitchers.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="hitters">
              <div className="rounded-md border bg-card shadow-sm">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40 text-xs">
                      <TableHead className="w-[180px]">Player</TableHead>
                      <TableHead className="w-[50px]">Src</TableHead>
                      <TableHead className="text-right">PA</TableHead>
                      <TableHead className="text-right">AVG</TableHead>
                      <TableHead className="text-right">HR</TableHead>
                      <TableHead className="text-right">RBI</TableHead>
                      <TableHead className="text-right">SB</TableHead>
                      <TableHead className="text-right">OPS</TableHead>
                      <TableHead className="text-right">wRC+</TableHead>
                      <TableHead className="text-right">WAR</TableHead>
                      <TableHead className="text-right w-[60px]">Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.hitters.map((h, i) => (
                      <TableRow key={i} className="hover:bg-muted/40">
                        <TableCell className="py-2">
                          <Link href={`/player/${encodeURIComponent(h.name)}`} className="hover:underline">
                            <div className="flex flex-col leading-tight">
                              <span className="font-semibold text-sm">{h.name}</span>
                              <span className="text-xs text-muted-foreground">{h.team} &middot; {h.position}</span>
                            </div>
                          </Link>
                        </TableCell>
                        <TableCell className="py-2">{sourceBadge(h.source)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{h.pa}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{h.avg.toFixed(3)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums font-medium">{h.hr}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{h.rbi}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{h.sb}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums font-medium">{h.ops.toFixed(3)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">
                          <span className={h.wrc_plus >= 120 ? "text-emerald-400 font-bold" : h.wrc_plus >= 100 ? "text-amber-400" : "text-rose-400"}>
                            {h.wrc_plus}
                          </span>
                        </TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{h.war.toFixed(1)}</TableCell>
                        <TableCell className="py-2 text-right">
                          <Badge className={`${valueBadge(h.ros_value)} text-xs w-12 justify-center font-bold tabular-nums`}>
                            {h.ros_value.toFixed(0)}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="pitchers">
              <div className="rounded-md border bg-card shadow-sm">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40 text-xs">
                      <TableHead className="w-[180px]">Player</TableHead>
                      <TableHead className="w-[50px]">Src</TableHead>
                      <TableHead className="text-right">IP</TableHead>
                      <TableHead className="text-right">ERA</TableHead>
                      <TableHead className="text-right">WHIP</TableHead>
                      <TableHead className="text-right">K</TableHead>
                      <TableHead className="text-right">QS</TableHead>
                      <TableHead className="text-right">FIP</TableHead>
                      <TableHead className="text-right">K-BB%</TableHead>
                      <TableHead className="text-right">WAR</TableHead>
                      <TableHead className="text-right w-[60px]">Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.pitchers.map((p, i) => (
                      <TableRow key={i} className="hover:bg-muted/40">
                        <TableCell className="py-2">
                          <Link href={`/player/${encodeURIComponent(p.name)}`} className="hover:underline">
                            <div className="flex flex-col leading-tight">
                              <span className="font-semibold text-sm">{p.name}</span>
                              <span className="text-xs text-muted-foreground">{p.team} &middot; {p.position}</span>
                            </div>
                          </Link>
                        </TableCell>
                        <TableCell className="py-2">{sourceBadge(p.source)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{p.ip.toFixed(1)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">
                          <span className={p.era <= 3.20 ? "text-emerald-400 font-bold" : p.era <= 4.00 ? "text-amber-400" : "text-rose-400"}>
                            {p.era.toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{p.whip.toFixed(2)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums font-medium">{p.k}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{p.qs}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{p.fip.toFixed(2)}</TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">
                          <span className={p.k_bb_pct >= 15 ? "text-emerald-400 font-bold" : p.k_bb_pct >= 10 ? "text-amber-400" : ""}>
                            {p.k_bb_pct.toFixed(1)}%
                          </span>
                        </TableCell>
                        <TableCell className="py-2 text-right text-sm tabular-nums">{p.war.toFixed(1)}</TableCell>
                        <TableCell className="py-2 text-right">
                          <Badge className={`${valueBadge(p.ros_value)} text-xs w-12 justify-center font-bold tabular-nums`}>
                            {p.ros_value.toFixed(0)}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <p className="mt-3 text-xs text-muted-foreground">
              Source: FanGraphs Steamer ROS &middot; {data.total_scanned} players scanned &middot; Updated {new Date(data.generated_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
            </p>
          </Tabs>
        )}
      </div>
    </main>
  )
}

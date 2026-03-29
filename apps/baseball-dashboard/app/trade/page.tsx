"use client"

import { useCallback, useEffect, useState, useRef } from "react"
import { useMutation } from "@tanstack/react-query"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { ArrowLeft, ArrowRightLeft, Search, TrendingUp, TrendingDown, Minus } from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from "recharts"

import type { TradeCategoryImpact, TradeResult } from "@fantasy/types"
import { TradeResultSchema } from "@fantasy/types"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type CategoryImpact = TradeCategoryImpact

type SearchResult = {
  name: string
  team: string
  type: string
  ros_value: number
}

function verdictIcon(v: string) {
  if (v === "gain") return <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
  if (v === "loss") return <TrendingDown className="h-3.5 w-3.5 text-red-400" />
  return <Minus className="h-3.5 w-3.5 text-slate-500" />
}

function verdictColor(v: string) {
  if (v === "gain") return "text-emerald-400"
  if (v === "loss") return "text-red-400"
  return "text-slate-500"
}

function rankBadge(rank: number | null) {
  if (rank == null) return "—"
  if (rank <= 4) return <Badge className="bg-emerald-600 text-white text-[10px] px-1.5">{rank}</Badge>
  if (rank <= 8) return <Badge className="bg-amber-600 text-white text-[10px] px-1.5">{rank}</Badge>
  return <Badge className="bg-red-600 text-white text-[10px] px-1.5">{rank}</Badge>
}

function CategoryImpactChart({ categories }: { categories: CategoryImpact[] }) {
  if (categories.length === 0) return null

  const chartData = categories.map(c => ({
    name: c.label,
    delta: c.rank_change,
    verdict: c.verdict,
  }))

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 p-4 mb-6">
      <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
        Rank Change by Category — green bars = improvement, red = decline
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis
            dataKey="name" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            interval={0} angle={-35} textAnchor="end" height={60}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            label={{ value: "Rank Δ", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "hsl(var(--muted-foreground))" } }}
            domain={["auto", "auto"]}
          />
          <RechartsTooltip
            content={({ payload }) => {
              if (!payload?.length) return null
              const d = payload[0].payload
              return (
                <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
                  <div className="font-semibold">{d.name}</div>
                  <div className="text-muted-foreground">
                    Rank change: {d.delta > 0 ? "+" : ""}{d.delta}
                  </div>
                </div>
              )
            }}
          />
          <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" opacity={0.3} />
          <Bar dataKey="delta" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.verdict === "gain" ? "#10b981" : entry.verdict === "loss" ? "#ef4444" : "#64748b"}
                opacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function TradePage() {
  const [giveQuery, setGiveQuery] = useState("")
  const [getQuery, setGetQuery] = useState("")
  const [giveName, setGiveName] = useState("")
  const [getName, setGetName] = useState("")
  const [giveResults, setGiveResults] = useState<SearchResult[]>([])
  const [getResults, setGetResults] = useState<SearchResult[]>([])
  const [showGiveDropdown, setShowGiveDropdown] = useState(false)
  const [showGetDropdown, setShowGetDropdown] = useState(false)
  const giveRef = useRef<HTMLDivElement>(null)
  const getRef = useRef<HTMLDivElement>(null)

  const tradeMutation = useMutation<TradeResult, Error>({
    mutationFn: async () => {
      const res = await fetch(
        `${API_BASE}/season/trade-analyzer?give=${encodeURIComponent(giveName)}&get=${encodeURIComponent(getName)}`,
        { cache: "no-store" }
      )
      if (!res.ok) throw new Error(`API ${res.status}`)
      return TradeResultSchema.parse(await res.json())
    },
  })

  const searchPlayers = useCallback(async (query: string, setter: (r: SearchResult[]) => void) => {
    if (query.length < 2) { setter([]); return }
    try {
      const res = await fetch(`${API_BASE}/season/trade-search?q=${encodeURIComponent(query)}&limit=8`, { cache: "no-store" })
      if (!res.ok) return
      const data = await res.json()
      setter(data.results || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => { searchPlayers(giveQuery, setGiveResults); setShowGiveDropdown(true) }, 300)
    return () => clearTimeout(t)
  }, [giveQuery, searchPlayers])

  useEffect(() => {
    const t = setTimeout(() => { searchPlayers(getQuery, setGetResults); setShowGetDropdown(true) }, 300)
    return () => clearTimeout(t)
  }, [getQuery, searchPlayers])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (giveRef.current && !giveRef.current.contains(e.target as Node)) setShowGiveDropdown(false)
      if (getRef.current && !getRef.current.contains(e.target as Node)) setShowGetDropdown(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const result = tradeMutation.data ?? null

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <header className="mb-6 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />Dashboard</Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <ArrowRightLeft className="h-6 w-6 text-primary" />
              Trade Analyzer
            </h1>
          </div>
        </header>

        {/* Trade Input */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-start mb-8">
          <div ref={giveRef} className="relative">
            <label className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-1.5 block">You Give</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search player to trade away..."
                value={giveQuery}
                onChange={e => { setGiveQuery(e.target.value); setGiveName("") }}
              />
            </div>
            {giveName && (
              <div className="mt-1.5 text-sm font-semibold text-red-400">{giveName}</div>
            )}
            {showGiveDropdown && giveResults.length > 0 && !giveName && (
              <div className="absolute z-50 w-full mt-1 rounded-lg border border-slate-700 bg-slate-900 shadow-xl max-h-60 overflow-y-auto">
                {giveResults.map(r => (
                  <button
                    key={r.name}
                    className="w-full text-left px-3 py-2 hover:bg-slate-800 flex items-center justify-between text-sm"
                    onClick={() => { setGiveName(r.name); setGiveQuery(r.name); setShowGiveDropdown(false) }}
                  >
                    <span>
                      <span className="font-medium">{r.name}</span>
                      <span className="text-muted-foreground ml-1.5">{r.team}</span>
                    </span>
                    <Badge variant="outline" className="text-[10px]">{r.type} · {r.ros_value}</Badge>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-end justify-center pb-2">
            <ArrowRightLeft className="h-5 w-5 text-muted-foreground" />
          </div>

          <div ref={getRef} className="relative">
            <label className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1.5 block">You Get</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search player to receive..."
                value={getQuery}
                onChange={e => { setGetQuery(e.target.value); setGetName("") }}
              />
            </div>
            {getName && (
              <div className="mt-1.5 text-sm font-semibold text-emerald-400">{getName}</div>
            )}
            {showGetDropdown && getResults.length > 0 && !getName && (
              <div className="absolute z-50 w-full mt-1 rounded-lg border border-slate-700 bg-slate-900 shadow-xl max-h-60 overflow-y-auto">
                {getResults.map(r => (
                  <button
                    key={r.name}
                    className="w-full text-left px-3 py-2 hover:bg-slate-800 flex items-center justify-between text-sm"
                    onClick={() => { setGetName(r.name); setGetQuery(r.name); setShowGetDropdown(false) }}
                  >
                    <span>
                      <span className="font-medium">{r.name}</span>
                      <span className="text-muted-foreground ml-1.5">{r.team}</span>
                    </span>
                    <Badge variant="outline" className="text-[10px]">{r.type} · {r.ros_value}</Badge>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-center mb-8">
          <Button
            size="lg"
            disabled={!giveName || !getName || tradeMutation.isPending}
            onClick={() => tradeMutation.mutate()}
            className="gap-2 px-8"
          >
            {tradeMutation.isPending ? "Analyzing..." : "Analyze Trade"}
            <ArrowRightLeft className="h-4 w-4" />
          </Button>
        </div>

        {tradeMutation.error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            {tradeMutation.error.message}. Make sure the season server is running on port 8001.
          </div>
        )}

        {result && result.categories.length > 0 && (
          <div className="space-y-6">
            <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-900/60 px-5 py-4">
              <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-1.5">
                    <span className="text-red-400 font-semibold">{result.give_player}</span>
                    {result.give_ros_value != null && (
                      <span className="text-xs text-muted-foreground">(ROS {result.give_ros_value})</span>
                    )}
                  </div>
                  <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
                  <div className="flex items-center gap-1.5">
                    <span className="text-emerald-400 font-semibold">{result.get_player}</span>
                    {result.get_ros_value != null && (
                      <span className="text-xs text-muted-foreground">(ROS {result.get_ros_value})</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className="bg-emerald-600 text-white text-xs">{result.cats_gained} gained</Badge>
                  <Badge className="bg-red-600 text-white text-xs">{result.cats_lost} lost</Badge>
                  <Badge variant="outline" className="text-xs">{result.cats_neutral} neutral</Badge>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className={`font-bold text-lg ${
                  result.win_probability_delta > 0 ? "text-emerald-400" :
                  result.win_probability_delta < 0 ? "text-red-400" : "text-slate-400"
                }`}>
                  {result.win_probability_delta > 0 ? "+" : ""}{result.win_probability_delta}% win prob
                </span>
                <span className="text-muted-foreground">{result.summary}</span>
              </div>
            </div>

            <CategoryImpactChart categories={result.categories} />

            <div className="rounded-lg border border-slate-200 dark:border-slate-700/60 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-200 dark:border-slate-700/60">
                    <TableHead className="w-[140px]">Category</TableHead>
                    <TableHead className="w-[60px]">Group</TableHead>
                    <TableHead className="w-[50px] text-center">Impact</TableHead>
                    <TableHead className="w-[80px] text-right">Give</TableHead>
                    <TableHead className="w-[80px] text-right">Get</TableHead>
                    <TableHead className="w-[70px] text-right">Delta</TableHead>
                    <TableHead className="w-[60px] text-center">Before</TableHead>
                    <TableHead className="w-[20px]" />
                    <TableHead className="w-[60px] text-center">After</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.categories.map(c => (
                    <TableRow key={c.stat_id} className="border-slate-200 dark:border-slate-700/40">
                      <TableCell className="font-medium">{c.label}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`text-[10px] ${
                          c.group === "batting" ? "border-sky-500/40 text-sky-400" : "border-orange-500/40 text-orange-400"
                        }`}>
                          {c.group === "batting" ? "BAT" : "PIT"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">{verdictIcon(c.verdict)}</TableCell>
                      <TableCell className="text-right tabular-nums text-red-400">
                        {c.before_value != null ? c.before_value.toFixed(c.before_value < 10 ? 3 : 1) : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-emerald-400">
                        {c.after_value != null ? c.after_value.toFixed(c.after_value < 10 ? 3 : 1) : "—"}
                      </TableCell>
                      <TableCell className={`text-right tabular-nums font-semibold ${verdictColor(c.verdict)}`}>
                        {c.delta != null ? `${c.delta > 0 ? "+" : ""}${c.delta.toFixed(3)}` : "—"}
                      </TableCell>
                      <TableCell className="text-center">{rankBadge(c.before_rank)}</TableCell>
                      <TableCell className="text-center text-muted-foreground">→</TableCell>
                      <TableCell className="text-center">{rankBadge(c.after_rank)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {result && result.categories.length === 0 && (
          <div className="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
            <p className="font-medium mb-1">No projection data available</p>
            <p className="text-sm">{result.summary}</p>
          </div>
        )}

        <footer className="text-center text-sm text-muted-foreground mt-10">
          <p>Trade analysis uses Steamer ROS projections + live league standings.</p>
          <p className="mt-1">Rank changes compare your projected stats against all 12 teams.</p>
        </footer>
      </div>
    </main>
  )
}

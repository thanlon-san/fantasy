"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import {
  ArrowUpDown, ArrowUp, ArrowDown,
  Swords, Home, Shield, TrendingUp, TrendingDown, Zap,
  Flame, Snowflake, Wind, CloudRain, Sun, Target, Activity,
  ChevronDown, BookOpen, Clock, DollarSign,
} from "lucide-react"
import type { Player } from "@fantasy/types"

type SortKey = "player" | "position" | "confidence" | "matchup" | "opponent"
type SortDirection = "asc" | "desc" | null

interface SignalChip {
  icon: React.ComponentType<{ className?: string }>
  chipColor: string   // Tailwind classes for bg + border + text on the pill
  label: string
  detail: string
}

// ─── Signal definitions ───────────────────────────────────────────────────────

const REASON_RULES: Array<{
  pattern: RegExp
  icon: React.ComponentType<{ className?: string }>
  chipColor: string
  label: string
}> = [
  { pattern: /hitter.friendly/i,            icon: Home,         chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Hitter-friendly park" },
  { pattern: /pitcher.friendly/i,            icon: Shield,       chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400",           label: "Pitcher-friendly park" },
  { pattern: /weak pitcher|easy matchup/i,   icon: Target,       chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Weak pitcher" },
  { pattern: /strong pitcher|elite pitcher|tough pitcher/i, icon: Target, chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400", label: "Tough pitcher" },
  { pattern: /hot streak|on fire/i,          icon: Flame,        chipColor: "bg-orange-500/15 border-orange-500/25 text-orange-400",     label: "Hot streak" },
  { pattern: /cold spell|slump/i,            icon: TrendingDown, chipColor: "bg-slate-400/15 border-slate-400/25 text-slate-400",        label: "Cold spell" },
  { pattern: /cold weather|cold temp|freezing|cold/i, icon: Snowflake, chipColor: "bg-sky-400/15 border-sky-400/25 text-sky-400",      label: "Cold weather" },
  { pattern: /hot weather|warm/i,            icon: Sun,          chipColor: "bg-amber-400/15 border-amber-400/25 text-amber-400",        label: "Warm weather" },
  { pattern: /wind/i,                        icon: Wind,         chipColor: "bg-slate-300/10 border-slate-400/20 text-slate-400",        label: "Wind factor" },
  { pattern: /rain/i,                        icon: CloudRain,    chipColor: "bg-blue-400/15 border-blue-400/25 text-blue-400",           label: "Rain risk" },
  { pattern: /platoon|handedness|L vs R|R vs L/i, icon: Zap,   chipColor: "bg-violet-400/15 border-violet-400/25 text-violet-400",      label: "Platoon advantage" },
  { pattern: /breakout|statcast/i,           icon: Activity,     chipColor: "bg-cyan-400/15 border-cyan-400/25 text-cyan-400",           label: "Breakout signal" },
  { pattern: /vegas total/i,                  icon: DollarSign,   chipColor: "bg-yellow-400/15 border-yellow-400/25 text-yellow-400",     label: "Vegas line" },
]

const LEGEND_ITEMS: Array<{
  icon: React.ComponentType<{ className?: string }>
  chipColor: string
  label: string
  description: string
}> = [
  { icon: Swords,       chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Matchup",        description: "Quality of the hitter vs. pitcher matchup (score 0–100)" },
  { icon: TrendingUp,   chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Form",           description: "Recent performance trend (score 0–100)" },
  { icon: Home,         chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Park (hitter)",  description: "Ballpark favors hitters (factor > 1.0)" },
  { icon: Shield,       chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400",           label: "Park (pitcher)", description: "Ballpark favors pitchers (factor < 1.0)" },
  { icon: Target,       chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",  label: "Weak pitcher",   description: "Favorable matchup against a weak or struggling pitcher" },
  { icon: Target,       chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400",           label: "Tough pitcher",  description: "Difficult matchup against an elite or hot pitcher" },
  { icon: Flame,        chipColor: "bg-orange-500/15 border-orange-500/25 text-orange-400",     label: "Hot streak",     description: "Player is on a hot streak recently" },
  { icon: TrendingDown, chipColor: "bg-slate-400/15 border-slate-400/25 text-slate-400",        label: "Cold spell",     description: "Player is in a cold stretch" },
  { icon: Snowflake,    chipColor: "bg-sky-400/15 border-sky-400/25 text-sky-400",              label: "Cold weather",   description: "Cold temperatures may suppress offense" },
  { icon: Sun,          chipColor: "bg-amber-400/15 border-amber-400/25 text-amber-400",        label: "Warm weather",   description: "Warm conditions — good for offense" },
  { icon: Wind,         chipColor: "bg-slate-300/10 border-slate-400/20 text-slate-400",        label: "Wind",           description: "Wind may suppress power numbers" },
  { icon: CloudRain,    chipColor: "bg-blue-400/15 border-blue-400/25 text-blue-400",           label: "Rain",           description: "Rain risk — potential postponement" },
  { icon: Zap,          chipColor: "bg-violet-400/15 border-violet-400/25 text-violet-400",     label: "Platoon",        description: "Favorable handedness matchup (e.g. LHH vs RHP)" },
  { icon: Activity,     chipColor: "bg-cyan-400/15 border-cyan-400/25 text-cyan-400",           label: "Breakout",       description: "Statcast metrics suggest a breakout or underlying improvement" },
  { icon: DollarSign,   chipColor: "bg-yellow-400/15 border-yellow-400/25 text-yellow-400",     label: "Vegas line",     description: "Vegas implied run total for today's game (higher = more runs expected)" },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseSignals(player: Player): SignalChip[] {
  const chips: SignalChip[] = []

  // Score-based chips — only surface when notable (avoids noise)
  if (player.matchup >= 80) {
    chips.push({ icon: Swords, chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Matchup", detail: `Matchup ${player.matchup}/100` })
  } else if (player.matchup < 45) {
    chips.push({ icon: Swords, chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400", label: "Matchup", detail: `Tough matchup ${player.matchup}/100` })
  }

  if (player.form >= 80) {
    chips.push({ icon: TrendingUp, chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Form", detail: `Form ${player.form}/100 — on a roll` })
  } else if (player.form < 40) {
    chips.push({ icon: TrendingDown, chipColor: "bg-slate-400/15 border-slate-400/25 text-slate-400", label: "Form", detail: `Form ${player.form}/100 — struggling` })
  }

  if (player.platoon >= 80) {
    chips.push({ icon: Zap, chipColor: "bg-violet-400/15 border-violet-400/25 text-violet-400", label: "Platoon", detail: `Platoon advantage ${player.platoon}/100` })
  }

  // Breakout boost
  if (player.breakout > 0) {
    chips.push({ icon: Activity, chipColor: "bg-cyan-400/15 border-cyan-400/25 text-cyan-400", label: "Breakout", detail: `Breakout signal (+${player.breakout})` })
  }

  // Vegas total
  if (player.vegas_total) {
    const env = player.vegas_total >= 10 ? "bg-emerald-500/15 border-emerald-500/25 text-emerald-400"
      : player.vegas_total <= 7 ? "bg-rose-500/15 border-rose-500/25 text-rose-400"
      : "bg-yellow-400/15 border-yellow-400/25 text-yellow-400"
    chips.push({ icon: DollarSign, chipColor: env, label: "Vegas", detail: `Game total: ${player.vegas_total}` })
  }

  // Reason-string chips — dedup by label so the same signal doesn't appear twice
  const seen = new Set<string>()
  for (const reason of player.reasons) {
    for (const rule of REASON_RULES) {
      if (rule.pattern.test(reason) && !seen.has(rule.label)) {
        seen.add(rule.label)
        chips.push({ icon: rule.icon, chipColor: rule.chipColor, label: rule.label, detail: reason })
      }
    }
  }

  return chips
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400"
  if (score >= 60) return "text-amber-400"
  return "text-rose-400"
}

function confidenceBadge(confidence: number): string {
  if (confidence >= 80) return "bg-emerald-600 hover:bg-emerald-700 text-white"
  if (confidence >= 65) return "bg-amber-600 hover:bg-amber-700 text-white"
  return "bg-slate-600 hover:bg-slate-700 text-white"
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SignalPill({ chip }: { chip: SignalChip }) {
  const Icon = chip.icon
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`inline-flex items-center justify-center w-6 h-6 rounded border ${chip.chipColor} cursor-default shrink-0`}>
          <Icon className="h-3 w-3" />
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-56 text-xs">
        <span className="font-semibold">{chip.label}</span>
        {chip.detail !== chip.label && <span className="block text-muted-foreground mt-0.5">{chip.detail}</span>}
      </TooltipContent>
    </Tooltip>
  )
}

function MiniScoreBar({ matchup, park, form, platoon }: { matchup: number; park: number; form: number; platoon: number }) {
  const segs = [
    { val: matchup, label: "Matchup" },
    { val: park, label: "Park" },
    { val: form, label: "Form" },
    { val: platoon, label: "Platoon" },
  ]
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-end gap-px cursor-default h-4 shrink-0">
          {segs.map((s, i) => (
            <span
              key={i}
              className={`w-1.5 rounded-sm ${s.val >= 75 ? "bg-emerald-500" : s.val >= 50 ? "bg-amber-500" : "bg-rose-500"}`}
              style={{ height: `${Math.max(3, Math.round((s.val / 100) * 16))}px` }}
            />
          ))}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs space-y-1">
        {segs.map((s, i) => (
          <div key={i} className="flex justify-between gap-4">
            <span className="text-muted-foreground">{s.label}</span>
            <span className={`font-semibold ${scoreColor(s.val)}`}>{s.val}</span>
          </div>
        ))}
      </TooltipContent>
    </Tooltip>
  )
}

function LineupLegend() {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground hover:text-foreground mt-2">
          <BookOpen className="h-3.5 w-3.5" />
          Signal legend
          <ChevronDown className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 p-3 rounded-lg border bg-muted/30 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {LEGEND_ITEMS.map((item, i) => {
            const Icon = item.icon
            return (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`inline-flex items-center justify-center w-6 h-6 rounded border shrink-0 ${item.chipColor}`}>
                  <Icon className="h-3 w-3" />
                </span>
                <div>
                  <div className="font-medium leading-tight">{item.label}</div>
                  <div className="text-muted-foreground leading-tight mt-0.5">{item.description}</div>
                </div>
              </div>
            )
          })}
          <div className="flex items-start gap-2 text-xs col-span-full mt-1 pt-2 border-t">
            <span className="inline-flex items-end gap-px h-4 shrink-0 mt-1">
              <span className="w-1.5 rounded-sm bg-emerald-500" style={{ height: "16px" }} />
              <span className="w-1.5 rounded-sm bg-amber-500" style={{ height: "10px" }} />
              <span className="w-1.5 rounded-sm bg-rose-500" style={{ height: "5px" }} />
              <span className="w-1.5 rounded-sm bg-emerald-500" style={{ height: "13px" }} />
            </span>
            <div>
              <div className="font-medium leading-tight">Mini-bar</div>
              <div className="text-muted-foreground leading-tight mt-0.5">4-segment sparkline showing Matchup · Park · Form · Platoon scores. Taller & greener = better.</div>
            </div>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

interface PlayerTableProps {
  players: Player[]
  variant?: "must-start" | "start" | "flex" | "bench" | "default"
}

export function PlayerTable({ players, variant = "default" }: PlayerTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDirection>(null)
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      if (sortDir === "asc") setSortDir("desc")
      else { setSortKey(null); setSortDir(null) }
    } else {
      setSortKey(key); setSortDir("asc")
    }
  }

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return players
    return [...players].sort((a, b) => {
      const av: string | number = a[sortKey]
      const bv: string | number = b[sortKey]
      const cmp = typeof av === "string"
        ? (av as string).toLowerCase().localeCompare((bv as string).toLowerCase())
        : (av as number) - (bv as number)
      return sortDir === "asc" ? cmp : -cmp
    })
  }, [players, sortKey, sortDir])

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown className="ml-1 h-3 w-3 opacity-40" />
    return sortDir === "asc"
      ? <ArrowUp className="ml-1 h-3 w-3" />
      : <ArrowDown className="ml-1 h-3 w-3" />
  }

  const rowBg = () => {
    if (variant === "must-start") return "bg-emerald-950/20 hover:bg-emerald-950/30"
    if (variant === "bench") return "hover:bg-muted/40 opacity-75"
    return "hover:bg-muted/50"
  }

  if (players.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">No players in this category</p>
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="rounded-md border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="border-b bg-muted/40 text-xs">
              <TableHead className="w-[170px]">
                <Button variant="ghost" size="sm" className="h-7 px-2 text-xs font-medium" onClick={() => handleSort("player")}>
                  Player <SortIcon col="player" />
                </Button>
              </TableHead>
              <TableHead className="w-[52px]">
                <Button variant="ghost" size="sm" className="h-7 px-2 text-xs font-medium" onClick={() => handleSort("position")}>
                  Pos <SortIcon col="position" />
                </Button>
              </TableHead>
              <TableHead className="w-[130px]">
                <Button variant="ghost" size="sm" className="h-7 px-2 text-xs font-medium" onClick={() => handleSort("opponent")}>
                  vs. <SortIcon col="opponent" />
                </Button>
              </TableHead>
              <TableHead className="w-[130px] hidden md:table-cell text-xs font-medium pl-3">Pitcher</TableHead>
              <TableHead className="w-[44px] hidden sm:table-cell text-xs font-medium pl-2">
                <Tooltip>
                  <TooltipTrigger className="flex items-center gap-1 cursor-help">
                    <Clock className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>Game time (ET)</TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="w-[52px]">
                <Button variant="ghost" size="sm" className="h-7 px-2 text-xs font-medium" onClick={() => handleSort("confidence")}>
                  Conf <SortIcon col="confidence" />
                </Button>
              </TableHead>
              <TableHead className="text-xs font-medium pl-3">Signals</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((player, i) => {
              const signals = parseSignals(player)
              return (
                <TableRow
                  key={i}
                  className={`cursor-pointer group ${rowBg()}`}
                  onClick={() => { setSelectedPlayer(player); setDialogOpen(true) }}
                >
                  {/* Player */}
                  <TableCell className="py-2">
                    <Link href={`/player/${encodeURIComponent(player.player)}`} className="hover:underline" onClick={e => e.stopPropagation()}>
                      <div className="flex flex-col leading-tight">
                        <span className="font-semibold text-sm">
                          {player.player}
                          {player.injury && (
                            <Badge variant="destructive" className="ml-1.5 text-[10px] px-1 py-0 align-middle">
                              {player.injury}
                            </Badge>
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground">{player.team}</span>
                      </div>
                    </Link>
                  </TableCell>

                  {/* Position */}
                  <TableCell className="py-2">
                    <Badge variant="outline" className="text-xs px-1.5 py-0 font-mono">
                      {player.position}
                    </Badge>
                  </TableCell>

                  {/* Matchup */}
                  <TableCell className="py-2 text-sm">
                    <div className="flex flex-col leading-tight">
                      <span className="font-medium">{player.opponent}</span>
                      <span className="text-xs text-muted-foreground">{player.team}</span>
                    </div>
                  </TableCell>

                  {/* Pitcher */}
                  <TableCell className="py-2 text-xs text-muted-foreground hidden md:table-cell">
                    {player.opponent_pitcher || "TBD"}
                  </TableCell>

                  {/* Time */}
                  <TableCell className="py-2 text-xs text-muted-foreground hidden sm:table-cell whitespace-nowrap">
                    {player.game_time?.replace(' ET', '') ?? '—'}
                  </TableCell>

                  {/* Confidence */}
                  <TableCell className="py-2" onClick={e => e.stopPropagation()}>
                    <Badge className={`${confidenceBadge(player.confidence)} text-xs w-10 justify-center font-bold tabular-nums`}>
                      {player.confidence}
                    </Badge>
                  </TableCell>

                  {/* Signals */}
                  <TableCell className="py-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <MiniScoreBar
                        matchup={player.matchup}
                        park={player.parkFactor}
                        form={player.form}
                        platoon={player.platoon}
                      />
                      {signals.map((chip, idx) => (
                        <SignalPill key={idx} chip={chip} />
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <LineupLegend />

      <PlayerDetailDialog
        player={selectedPlayer}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </TooltipProvider>
  )
}

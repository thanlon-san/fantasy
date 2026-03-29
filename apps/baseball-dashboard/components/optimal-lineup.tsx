"use client"

/**
 * OptimalLineupView
 *
 * Assigns players to fantasy roster slots using a constraint-ordered greedy
 * algorithm:
 *   1. Process slots from most- to least-constrained (fewest eligible players)
 *   2. For each slot pick the highest-confidence eligible player not yet used
 *   3. UTIL is filled last — and prefers "risky" players (rain / late game)
 *      so they're easy to swap if the game is postponed or you want to wait
 *
 * Roster layout defaults to a standard 12-team Yahoo H2H league:
 *   C · 1B · 2B · 3B · SS · OF · OF · OF · UTIL
 *   SP · SP · SP · SP · RP · RP · RP
 */

import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import {
  Swords, Home, Shield, TrendingUp, TrendingDown, Zap,
  Flame, Snowflake, Wind, CloudRain, Sun, Target, Activity,
  AlertTriangle, BookOpen, ChevronDown, ExternalLink, Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { useToast } from "@/components/ui/use-toast"

// ─── Types ────────────────────────────────────────────────────────────────────

type Player = {
  player: string
  player_key?: string
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

// Map our slot labels to Yahoo's accepted position values
const YAHOO_SLOT: Record<string, string> = {
  C: "C", "1B": "1B", "2B": "2B", "3B": "3B", SS: "SS",
  OF: "OF", UTIL: "Util", SP: "SP", RP: "RP", P: "P", BN: "BN",
}

interface RosterSlot {
  id: string
  label: string
  positions: string[]
  group: "hitter" | "pitcher"
  isUtil?: boolean
}

// ─── Roster configuration ─────────────────────────────────────────────────────
// Standard 12-team Yahoo H2H Baseball (adjust slot counts to match your league)

const ROSTER_SLOTS: RosterSlot[] = [
  // ── Hitters (9 active slots) ──
  { id: "C",    label: "C",    positions: ["C"],                               group: "hitter" },
  { id: "1B",   label: "1B",   positions: ["1B"],                             group: "hitter" },
  { id: "2B",   label: "2B",   positions: ["2B"],                             group: "hitter" },
  { id: "3B",   label: "3B",   positions: ["3B"],                             group: "hitter" },
  { id: "SS",   label: "SS",   positions: ["SS"],                             group: "hitter" },
  { id: "OF1",  label: "OF",   positions: ["OF"],                             group: "hitter" },
  { id: "OF2",  label: "OF",   positions: ["OF"],                             group: "hitter" },
  { id: "OF3",  label: "OF",   positions: ["OF"],                             group: "hitter" },
  { id: "UTIL", label: "UTIL", positions: ["C","1B","2B","3B","SS","OF"],     group: "hitter", isUtil: true },
  // ── Pitchers (8 active slots: 2 SP + 2 RP + 4 P) ──
  { id: "SP1",  label: "SP",   positions: ["SP"],                             group: "pitcher" },
  { id: "SP2",  label: "SP",   positions: ["SP"],                             group: "pitcher" },
  { id: "RP1",  label: "RP",   positions: ["RP"],                             group: "pitcher" },
  { id: "RP2",  label: "RP",   positions: ["RP"],                             group: "pitcher" },
  // P slots accept any pitcher (SP, RP, or SP,RP eligible)
  { id: "P1",   label: "P",    positions: ["SP", "RP"],                       group: "pitcher" },
  { id: "P2",   label: "P",    positions: ["SP", "RP"],                       group: "pitcher" },
  { id: "P3",   label: "P",    positions: ["SP", "RP"],                       group: "pitcher" },
  { id: "P4",   label: "P",    positions: ["SP", "RP"],                       group: "pitcher" },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getPositions(player: Player): string[] {
  return player.position.split(",").map((s) => s.trim())
}

function canFillSlot(player: Player, slot: RosterSlot): boolean {
  const pp = getPositions(player)
  // SP,RP eligible players can fill SP or RP slots
  const hasSP = pp.includes("SP")
  const hasRP = pp.includes("RP")
  return slot.positions.some((sp) => {
    if (sp === "SP") return hasSP
    if (sp === "RP") return hasRP || (hasSP && hasRP) // SP,RP can fill RP too
    return pp.includes(sp)
  })
}

function isRisky(player: Player): { risky: boolean; reason: string } {
  // Rain / weather risk
  if (player.reasons.some((r) => /rain/i.test(r))) {
    return { risky: true, reason: "Rain risk — game may be postponed" }
  }
  if (player.reasons.some((r) => /wind suppress/i.test(r))) {
    return { risky: true, reason: "Wind suppression — power at risk" }
  }
  // Late game (7:30 PM ET or later → west coast / evening game)
  if (player.game_time) {
    const m = player.game_time.match(/(\d+):(\d+)\s*(AM|PM)/i)
    if (m) {
      let h = parseInt(m[1])
      const mins = parseInt(m[2])
      const isPM = m[3].toLowerCase() === "pm"
      if (isPM && h !== 12) h += 12
      if (!isPM && h === 12) h = 0
      if (h > 19 || (h === 19 && mins >= 30)) {
        return { risky: true, reason: `Late game (${player.game_time}) — easier to monitor before finalising` }
      }
    }
  }
  return { risky: false, reason: "" }
}

function buildOptimalLineup(players: Player[]) {
  const byConf = [...players].sort((a, b) => b.confidence - a.confidence)
  const assigned = new Map<string, Player>()
  const used = new Set<string>()

  // Count eligible players per slot → sort by fewest eligible first (most constrained)
  const slotOrder = ROSTER_SLOTS.filter((s) => !s.isUtil).sort((a, b) => {
    const ca = byConf.filter((p) => canFillSlot(p, a)).length
    const cb = byConf.filter((p) => canFillSlot(p, b)).length
    return ca - cb
  })
  const utilSlots = ROSTER_SLOTS.filter((s) => s.isUtil)

  for (const slot of [...slotOrder, ...utilSlots]) {
    const eligible = byConf.filter((p) => !used.has(p.player) && canFillSlot(p, slot))
    if (eligible.length === 0) continue

    let chosen: Player
    if (slot.isUtil) {
      // Prefer the best risky player for UTIL so it's easy to swap
      const risky = eligible.filter((p) => isRisky(p).risky)
      chosen = risky.length > 0 ? risky[0] : eligible[0]
    } else {
      chosen = eligible[0]
    }

    assigned.set(slot.id, chosen)
    used.add(chosen.player)
  }

  const bench = byConf.filter((p) => !used.has(p.player))

  return {
    slots: ROSTER_SLOTS.map((slot) => ({ slot, player: assigned.get(slot.id) ?? null })),
    bench,
  }
}

// ─── Signal chip utilities (shared with player-table) ─────────────────────────

const REASON_RULES = [
  { pattern: /hitter.friendly/i,   icon: Home,         chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Hitter-friendly park" },
  { pattern: /pitcher.friendly/i,  icon: Shield,       chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400",         label: "Pitcher-friendly park" },
  { pattern: /weak pitcher/i,      icon: Target,       chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Weak pitcher" },
  { pattern: /strong pitcher|elite pitcher|tough pitcher/i, icon: Target, chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400", label: "Tough pitcher" },
  { pattern: /hot streak|on fire/i, icon: Flame,       chipColor: "bg-orange-500/15 border-orange-500/25 text-orange-400",   label: "Hot streak" },
  { pattern: /cold spell|slump/i,  icon: TrendingDown, chipColor: "bg-slate-400/15 border-slate-400/25 text-slate-400",      label: "Cold spell" },
  { pattern: /cold weather|cold temp|freezing|cold/i, icon: Snowflake, chipColor: "bg-sky-400/15 border-sky-400/25 text-sky-400", label: "Cold weather" },
  { pattern: /hot weather|warm/i,  icon: Sun,          chipColor: "bg-amber-400/15 border-amber-400/25 text-amber-400",      label: "Warm weather" },
  { pattern: /wind/i,              icon: Wind,         chipColor: "bg-slate-300/10 border-slate-400/20 text-slate-400",      label: "Wind" },
  { pattern: /rain/i,              icon: CloudRain,    chipColor: "bg-blue-400/15 border-blue-400/25 text-blue-400",         label: "Rain risk" },
  { pattern: /platoon|handedness/i, icon: Zap,         chipColor: "bg-violet-400/15 border-violet-400/25 text-violet-400",  label: "Platoon" },
  { pattern: /breakout|statcast/i, icon: Activity,     chipColor: "bg-cyan-400/15 border-cyan-400/25 text-cyan-400",        label: "Breakout" },
]

interface SignalChip { icon: React.ComponentType<{ className?: string }>; chipColor: string; label: string; detail: string }

function parseSignals(player: Player): SignalChip[] {
  const chips: SignalChip[] = []
  if (player.matchup >= 80) chips.push({ icon: Swords, chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Matchup", detail: `Matchup ${player.matchup}/100` })
  else if (player.matchup < 45) chips.push({ icon: Swords, chipColor: "bg-rose-500/15 border-rose-500/25 text-rose-400", label: "Matchup", detail: `Tough matchup ${player.matchup}/100` })
  if (player.form >= 80) chips.push({ icon: TrendingUp, chipColor: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400", label: "Form", detail: `Form ${player.form}/100` })
  else if (player.form < 40) chips.push({ icon: TrendingDown, chipColor: "bg-slate-400/15 border-slate-400/25 text-slate-400", label: "Form", detail: `Form ${player.form}/100` })
  if (player.platoon >= 80) chips.push({ icon: Zap, chipColor: "bg-violet-400/15 border-violet-400/25 text-violet-400", label: "Platoon", detail: `Platoon advantage ${player.platoon}/100` })
  if (player.breakout > 0) chips.push({ icon: Activity, chipColor: "bg-cyan-400/15 border-cyan-400/25 text-cyan-400", label: "Breakout", detail: `Breakout signal (+${player.breakout})` })
  const seen = new Set<string>()
  for (const r of player.reasons) {
    for (const rule of REASON_RULES) {
      if (rule.pattern.test(r) && !seen.has(rule.label)) {
        seen.add(rule.label)
        chips.push({ icon: rule.icon, chipColor: rule.chipColor, label: rule.label, detail: r })
      }
    }
  }
  return chips
}

function scoreColor(v: number) {
  return v >= 80 ? "text-emerald-400" : v >= 60 ? "text-amber-400" : "text-rose-400"
}

function confBadge(c: number) {
  return c >= 80 ? "bg-emerald-600 text-white" : c >= 65 ? "bg-amber-600 text-white" : "bg-slate-600 text-white"
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

function MiniBar({ m, p, f, pl }: { m: number; p: number; f: number; pl: number }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-end gap-px cursor-default h-4 shrink-0">
          {[{ v: m, l: "Matchup" }, { v: p, l: "Park" }, { v: f, l: "Form" }, { v: pl, l: "Platoon" }].map((s, i) => (
            <span key={i} className={`w-1.5 rounded-sm ${s.v >= 75 ? "bg-emerald-500" : s.v >= 50 ? "bg-amber-500" : "bg-rose-500"}`}
              style={{ height: `${Math.max(3, Math.round((s.v / 100) * 16))}px` }} />
          ))}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs space-y-1">
        {[{ l: "Matchup", v: m }, { l: "Park", v: p }, { l: "Form", v: f }, { l: "Platoon", v: pl }].map((s, i) => (
          <div key={i} className="flex justify-between gap-4">
            <span className="text-muted-foreground">{s.l}</span>
            <span className={`font-semibold ${scoreColor(s.v)}`}>{s.v}</span>
          </div>
        ))}
      </TooltipContent>
    </Tooltip>
  )
}

function EmptySlotRow({ slot }: { slot: RosterSlot }) {
  return (
    <tr className="border-b border-border/50 opacity-40">
      <td className="py-2 pl-3 w-12">
        <span className="text-xs font-mono font-bold text-muted-foreground">{slot.label}</span>
      </td>
      <td colSpan={6} className="py-2 pl-2 text-xs text-muted-foreground italic">No eligible player with a game today</td>
    </tr>
  )
}

function PlayerRow({
  slot, player, isUtil, utilReason, onClick
}: {
  slot: RosterSlot; player: Player; isUtil?: boolean; utilReason?: string; onClick: () => void
}) {
  const chips = parseSignals(player)
  const riskBg = isUtil && utilReason ? "bg-amber-500/5" : ""

  return (
    <tr
      className={`border-b border-border/50 cursor-pointer hover:bg-muted/40 transition-colors group ${riskBg}`}
      onClick={onClick}
    >
      {/* Slot label */}
      <td className="py-2 pl-3 w-12">
        <div className="flex items-center gap-1">
          <span className={`text-xs font-mono font-bold ${isUtil ? "text-amber-400" : "text-muted-foreground"}`}>
            {slot.label}
          </span>
          {isUtil && utilReason && (
            <Tooltip>
              <TooltipTrigger asChild>
                <AlertTriangle className="h-3 w-3 text-amber-400 cursor-help" />
              </TooltipTrigger>
              <TooltipContent className="max-w-52 text-xs">
                <span className="font-semibold text-amber-400">Placed in UTIL</span>
                <span className="block text-muted-foreground mt-0.5">{utilReason}</span>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </td>

      {/* Player name + team */}
      <td className="py-2 pl-2 min-w-[150px]">
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-sm">{player.player}</span>
          <span className="text-xs text-muted-foreground">{player.team}</span>
        </div>
      </td>

      {/* Eligible position (not the slot) */}
      <td className="py-2 px-2 hidden sm:table-cell">
        <Badge variant="outline" className="text-xs px-1.5 py-0 font-mono">{player.position}</Badge>
      </td>

      {/* Matchup */}
      <td className="py-2 px-2">
        <div className="flex flex-col leading-tight text-sm">
          <span className="font-medium">{player.opponent}</span>
          <span className="text-xs text-muted-foreground hidden md:block">{player.opponent_pitcher ?? "TBD"}</span>
        </div>
      </td>

      {/* Game time */}
      <td className="py-2 px-2 text-xs text-muted-foreground whitespace-nowrap hidden sm:table-cell">
        {player.game_time?.replace(" ET", "") ?? "—"}
      </td>

      {/* Confidence */}
      <td className="py-2 px-2">
        <Badge className={`${confBadge(player.confidence)} text-xs w-10 justify-center font-bold tabular-nums`}>
          {player.confidence}
        </Badge>
      </td>

      {/* Signals */}
      <td className="py-2 pl-2 pr-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <MiniBar m={player.matchup} p={player.parkFactor} f={player.form} pl={player.platoon} />
          {chips.map((chip, i) => <SignalPill key={i} chip={chip} />)}
        </div>
      </td>
    </tr>
  )
}

function SectionDivider({ label }: { label: string }) {
  return (
    <tr>
      <td colSpan={7} className="pt-4 pb-1 pl-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
      </td>
    </tr>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────

interface OptimalLineupViewProps {
  players: Player[]
  notPlayingPlayers?: { player: string; player_key?: string }[]
  apiBase?: string
  teamKey?: string
}

export function OptimalLineupView({
  players, notPlayingPlayers = [], apiBase, teamKey,
}: OptimalLineupViewProps) {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [legendOpen, setLegendOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [sending, setSending] = useState(false)
  const { toast } = useToast()

  const { slots, bench } = useMemo(() => buildOptimalLineup(players), [players])

  // Build the full assignment list for the Yahoo API call
  const buildAssignments = () => {
    const out: { player_key: string; position: string; name: string }[] = []
    for (const { slot, player } of slots) {
      if (player?.player_key) {
        out.push({ player_key: player.player_key, position: YAHOO_SLOT[slot.label] ?? slot.label, name: player.player })
      }
    }
    for (const p of bench) {
      if (p.player_key) out.push({ player_key: p.player_key, position: "BN", name: p.player })
    }
    for (const p of notPlayingPlayers) {
      if (p.player_key) out.push({ player_key: p.player_key, position: "BN", name: p.player })
    }
    return out
  }

  const assignments = useMemo(buildAssignments, [slots, bench, notPlayingPlayers])
  const hasKeys = assignments.length > 0
  const today = new Date().toISOString().split("T")[0]

  const handleSetLineup = async () => {
    if (!apiBase || !teamKey) return
    setSending(true)
    setConfirmOpen(false)
    try {
      const res = await fetch(`${apiBase}/api/set-lineup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_key: teamKey,
          date: today,
          assignments: assignments.map(({ player_key, position }) => ({ player_key, position })),
        }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        toast({ title: "✅ Lineup set in Yahoo!", description: `${assignments.filter(a => a.position !== "BN").length} active slots updated for ${today}.` })
      } else {
        toast({ title: "Yahoo API error", description: data.detail ?? data.error ?? "Unknown error", variant: "destructive" })
      }
    } catch (e) {
      toast({ title: "Network error", description: String(e), variant: "destructive" })
    } finally {
      setSending(false)
    }
  }

  const hitterSlots = slots.filter((s) => s.slot.group === "hitter")
  const pitcherSlots = slots.filter((s) => s.slot.group === "pitcher")

  if (players.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No lineup data available</p>
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="rounded-md border bg-card shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/40">
              <th className="py-2 pl-3 w-12 text-left text-xs font-medium text-muted-foreground">Slot</th>
              <th className="py-2 pl-2 text-left text-xs font-medium text-muted-foreground">Player</th>
              <th className="py-2 px-2 text-left text-xs font-medium text-muted-foreground hidden sm:table-cell">Pos</th>
              <th className="py-2 px-2 text-left text-xs font-medium text-muted-foreground">vs.</th>
              <th className="py-2 px-2 text-left text-xs font-medium text-muted-foreground hidden sm:table-cell">Time</th>
              <th className="py-2 px-2 text-left text-xs font-medium text-muted-foreground">Conf</th>
              <th className="py-2 pl-2 pr-3 text-left text-xs font-medium text-muted-foreground">Signals</th>
            </tr>
          </thead>
          <tbody>
            <SectionDivider label="Hitters" />
            {hitterSlots.map(({ slot, player }) => {
              if (!player) return <EmptySlotRow key={slot.id} slot={slot} />
              const { risky, reason } = isRisky(player)
              const inUtil = slot.isUtil
              return (
                <PlayerRow
                  key={slot.id}
                  slot={slot}
                  player={player}
                  isUtil={inUtil && risky}
                  utilReason={inUtil && risky ? reason : undefined}
                  onClick={() => { setSelectedPlayer(player); setDialogOpen(true) }}
                />
              )
            })}

            <SectionDivider label="Pitchers" />
            {pitcherSlots.map(({ slot, player }) => {
              if (!player) return <EmptySlotRow key={slot.id} slot={slot} />
              return (
                <PlayerRow
                  key={slot.id}
                  slot={slot}
                  player={player}
                  onClick={() => { setSelectedPlayer(player); setDialogOpen(true) }}
                />
              )
            })}
          </tbody>
        </table>
      </div>

      {bench.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 pl-1">
            Bench ({bench.length})
          </p>
          <div className="rounded-md border bg-card shadow-sm overflow-hidden opacity-75">
            <table className="w-full">
              <tbody>
                {bench.map((player) => {
                  const { risky, reason } = isRisky(player)
                  return (
                    <PlayerRow
                      key={player.player}
                      slot={{ id: "BN", label: "BN", positions: [], group: "hitter" }}
                      player={player}
                      isUtil={risky}
                      utilReason={risky ? reason : undefined}
                      onClick={() => { setSelectedPlayer(player); setDialogOpen(true) }}
                    />
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      <Collapsible open={legendOpen} onOpenChange={setLegendOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground hover:text-foreground mt-2">
            <BookOpen className="h-3.5 w-3.5" />
            Signal legend
            <ChevronDown className={`h-3 w-3 transition-transform ${legendOpen ? "rotate-180" : ""}`} />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2 p-3 rounded-lg border bg-muted/30 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 text-xs">
            {[
              { Icon: AlertTriangle, color: "text-amber-400 bg-amber-400/15 border-amber-400/25", label: "UTIL risk flag", desc: "Player placed in UTIL due to rain risk or late game — easy to swap" },
              { Icon: Swords,       color: "text-emerald-400 bg-emerald-500/15 border-emerald-500/25", label: "Matchup",       desc: "Quality of today's hitter vs. pitcher matchup (≥80 shown)" },
              { Icon: TrendingUp,   color: "text-emerald-400 bg-emerald-500/15 border-emerald-500/25", label: "Hot form",      desc: "Player is trending upward in recent performance" },
              { Icon: TrendingDown, color: "text-slate-400 bg-slate-400/15 border-slate-400/25",       label: "Cold form",     desc: "Player is in a cold stretch" },
              { Icon: Home,         color: "text-emerald-400 bg-emerald-500/15 border-emerald-500/25", label: "Hitter park",   desc: "Ballpark favors hitters today" },
              { Icon: Shield,       color: "text-rose-400 bg-rose-500/15 border-rose-500/25",          label: "Pitcher park",  desc: "Ballpark favors pitchers today" },
              { Icon: Target,       color: "text-emerald-400 bg-emerald-500/15 border-emerald-500/25", label: "Weak pitcher",  desc: "Favorable matchup against a struggling pitcher" },
              { Icon: Target,       color: "text-rose-400 bg-rose-500/15 border-rose-500/25",          label: "Tough pitcher", desc: "Difficult matchup against an elite pitcher" },
              { Icon: Flame,        color: "text-orange-400 bg-orange-500/15 border-orange-500/25",    label: "Hot streak",    desc: "Player on a hot streak" },
              { Icon: Snowflake,    color: "text-sky-400 bg-sky-400/15 border-sky-400/25",             label: "Cold weather",  desc: "Cold temps may suppress offense" },
              { Icon: Wind,         color: "text-slate-400 bg-slate-300/10 border-slate-400/20",       label: "Wind",          desc: "Wind conditions in play" },
              { Icon: CloudRain,    color: "text-blue-400 bg-blue-400/15 border-blue-400/25",          label: "Rain",          desc: "Rain risk — monitor for postponement" },
              { Icon: Zap,          color: "text-violet-400 bg-violet-400/15 border-violet-400/25",    label: "Platoon",       desc: "Favourable handedness matchup" },
              { Icon: Activity,     color: "text-cyan-400 bg-cyan-400/15 border-cyan-400/25",          label: "Breakout",      desc: "Statcast signals an underlying breakout" },
            ].map(({ Icon, color, label, desc }, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`inline-flex items-center justify-center w-6 h-6 rounded border shrink-0 ${color}`}>
                  <Icon className="h-3 w-3" />
                </span>
                <div>
                  <div className="font-medium leading-tight">{label}</div>
                  <div className="text-muted-foreground leading-tight mt-0.5">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Set Lineup button */}
      {apiBase && teamKey && (
        <div className="mt-3 flex items-center gap-3">
          <Button
            size="sm"
            disabled={!hasKeys || sending}
            onClick={() => setConfirmOpen(true)}
            className="gap-2"
          >
            {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ExternalLink className="h-3.5 w-3.5" />}
            {sending ? "Setting lineup…" : "Set Lineup in Yahoo"}
          </Button>
          {!hasKeys && (
            <span className="text-xs text-muted-foreground">
              Player keys load after the next data refresh (8am ET)
            </span>
          )}
        </div>
      )}

      {/* Confirmation dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Set lineup in Yahoo?</DialogTitle>
            <DialogDescription>
              This will push the following assignments to Yahoo Fantasy Baseball for <strong>{today}</strong>.
              Yahoo will reject any invalid slot for a player's eligibility.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-64 overflow-y-auto text-sm space-y-1 my-2">
            {assignments.filter(a => a.position !== "BN").map((a, i) => (
              <div key={i} className="flex justify-between gap-4">
                <span className="font-mono text-xs text-muted-foreground w-10 shrink-0">{a.position}</span>
                <span className="flex-1">{a.name}</span>
              </div>
            ))}
            {assignments.filter(a => a.position === "BN").length > 0 && (
              <p className="text-xs text-muted-foreground pt-1 border-t mt-1">
                + {assignments.filter(a => a.position === "BN").length} players set to bench
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Cancel</Button>
            <Button onClick={handleSetLineup} className="gap-2">
              <ExternalLink className="h-3.5 w-3.5" />
              Confirm & Set
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <PlayerDetailDialog player={selectedPlayer} open={dialogOpen} onOpenChange={setDialogOpen} />
    </TooltipProvider>
  )
}

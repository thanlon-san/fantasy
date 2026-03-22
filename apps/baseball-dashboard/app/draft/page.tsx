"use client"

import { useState, useEffect, useMemo } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ThemeToggle } from "@/components/theme-toggle"
import {
  ArrowLeft,
  Star,
  Clock,
  Trophy,
  AlertCircle,
  CheckCircle2,
  Info,
  Users,
  Zap,
} from "lucide-react"

const BASE_PATH = process.env.NODE_ENV === 'production' ? '/fantasy/baseball' : ''

// ─── Types ────────────────────────────────────────────────────────────────────

type LeagueKeeper = {
  player: string
  position: string
  round: number
  adp?: number
}

type LeagueTeam = {
  team_name: string
  owner: string
  is_my_team: boolean
  keepers: LeagueKeeper[]
}

type LeagueKeepersData = {
  season: number
  league_name: string
  confirmed: boolean
  last_updated: string
  teams: LeagueTeam[]
}

type MyKeeper = {
  player: string
  position?: string
  round: number | string
  adp: number
  surplus: string
  value: string
  years_remaining?: number
  reason?: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getDraftCountdown(draftDate: string): {
  days: number
  hours: number
  label: string
  isPast: boolean
} {
  const now = new Date()
  const target = new Date(draftDate)
  const diffMs = target.getTime() - now.getTime()

  if (diffMs <= 0) {
    const daysPast = Math.floor(Math.abs(diffMs) / (1000 * 60 * 60 * 24))
    return { days: daysPast, hours: 0, label: daysPast === 0 ? "Draft day!" : `${daysPast}d ago`, isPast: true }
  }

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  return {
    days,
    hours,
    label: days === 0 ? `${hours}h` : days === 1 ? `1 day` : `${days} days`,
    isPast: false,
  }
}

// Position badge color classes
function positionColor(pos: string): string {
  const p = pos.split(',')[0].trim()
  if (["SP", "RP", "P"].includes(p)) return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
  if (["C"].includes(p)) return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
  if (["1B", "2B", "3B", "SS"].includes(p)) return "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
  return "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300"
}

// ─── My Keepers Strip (compact) ───────────────────────────────────────────────

function MyKeepersStrip({ keepers, keeperRounds }: { keepers: MyKeeper[]; keeperRounds: number[] }) {
  if (keepers.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card px-4 py-2.5">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide mr-1">
        Keepers
      </span>
      {keepers.map((k, i) => {
        const surplus = parseInt(k.surplus.replace('+', ''))
        return (
          <div
            key={i}
            className="flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-sm"
          >
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${positionColor(k.position || '')}`}>
              {k.position}
            </span>
            <span className="font-medium">{k.player}</span>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground text-xs">Rd {k.round}</span>
            <span className={`text-xs font-semibold ${surplus > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {k.surplus}
            </span>
          </div>
        )
      })}
      <span className="ml-auto text-xs text-muted-foreground">
        Locks rounds {keeperRounds.sort((a, b) => a - b).join(', ')}
      </span>
    </div>
  )
}

// ─── League Keeper Board ──────────────────────────────────────────────────────

function LeagueKeeperBoard({ teams }: { teams: LeagueTeam[] }) {
  const teamsWithKeepers = teams.filter(t => t.keepers.length > 0)
  const teamsWithoutKeepers = teams.filter(t => t.keepers.length === 0)
  const totalConfirmed = teamsWithKeepers.length
  const totalTeams = teams.length

  // Build a round → [{ team, keeper }] map for the round impact grid
  const roundMap = useMemo(() => {
    const map: Record<number, { team: LeagueTeam; keeper: LeagueKeeper }[]> = {}
    teams.forEach(team => {
      team.keepers.forEach(keeper => {
        if (!map[keeper.round]) map[keeper.round] = []
        map[keeper.round].push({ team, keeper })
      })
    })
    return map
  }, [teams])

  const occupiedRounds = Object.keys(roundMap).map(Number).sort((a, b) => a - b)

  if (teamsWithKeepers.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
        <Info className="h-10 w-10 mx-auto mb-3 opacity-30" />
        <p className="font-medium mb-1">No league keeper data yet</p>
        <p className="text-sm">
          Edit{" "}
          <code className="bg-muted px-1.5 py-0.5 rounded text-xs">
            public/api/league_keepers.json
          </code>{" "}
          to add other teams&apos; keepers as you learn them.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Confirmation status */}
      <div className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm border ${
        totalConfirmed === totalTeams
          ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/20 dark:border-emerald-900 dark:text-emerald-300'
          : 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/20 dark:border-amber-900 dark:text-amber-300'
      }`}>
        {totalConfirmed === totalTeams
          ? <CheckCircle2 className="h-4 w-4 shrink-0" />
          : <AlertCircle className="h-4 w-4 shrink-0" />
        }
        <span>
          <span className="font-semibold">{totalConfirmed} of {totalTeams}</span> teams have confirmed keepers.
          {totalTeams - totalConfirmed > 0 && ` ${totalTeams - totalConfirmed} team${totalTeams - totalConfirmed > 1 ? 's' : ''} still unknown.`}
        </span>
      </div>

      {/* By-team breakdown */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {teams.map(team => (
          <div
            key={team.team_name}
            className={`rounded-lg border bg-card p-4 space-y-3 ${
              team.is_my_team ? 'border-primary/40 ring-1 ring-primary/20' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold flex items-center gap-1.5">
                  {team.team_name}
                  {team.is_my_team && (
                    <Badge variant="secondary" className="text-[10px] py-0">You</Badge>
                  )}
                </div>
                {team.owner && (
                  <div className="text-xs text-muted-foreground">{team.owner}</div>
                )}
              </div>
              <Badge variant={team.keepers.length > 0 ? "default" : "outline"}>
                {team.keepers.length > 0 ? `${team.keepers.length} keeper${team.keepers.length !== 1 ? 's' : ''}` : 'TBD'}
              </Badge>
            </div>

            {team.keepers.length > 0 ? (
              <div className="space-y-2">
                {team.keepers.map((k, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${positionColor(k.position)}`}>
                        {k.position}
                      </span>
                      <span className="font-medium">{k.player}</span>
                    </div>
                    <span className="text-muted-foreground font-mono text-xs">Rd {k.round}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No keepers entered yet</p>
            )}
          </div>
        ))}
      </div>

      {/* Round Impact Table */}
      {occupiedRounds.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
            Draft Round Impact — Rounds with Keeper Locks
          </h3>
          <div className="rounded-md border bg-card shadow-sm overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="px-4 py-3 w-20">Round</TableHead>
                  <TableHead className="px-4 py-3">Keeper Slots Taken</TableHead>
                  <TableHead className="px-4 py-3 text-right">Free Picks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {occupiedRounds.map(round => {
                  const entries = roundMap[round]
                  const freeSlots = teams.length - entries.length
                  return (
                    <TableRow key={round} className={entries.some(e => e.team.is_my_team) ? 'bg-primary/5' : ''}>
                      <TableCell className="px-4 py-3 font-mono font-bold">
                        Rd {round}
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          {entries.map((e, i) => (
                            <div key={i} className={`flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 ${
                              e.team.is_my_team
                                ? 'bg-primary/10 text-primary font-semibold'
                                : 'bg-muted text-muted-foreground'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${positionColor(e.keeper.position).split(' ')[0]}`} />
                              <span className="font-medium">{e.keeper.player}</span>
                              <span className="opacity-60">({e.team.is_my_team ? 'You' : e.team.team_name})</span>
                            </div>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-right">
                        <span className={`font-semibold ${freeSlots > 5 ? 'text-emerald-600' : freeSlots > 2 ? 'text-amber-600' : 'text-red-500'}`}>
                          {freeSlots}
                        </span>
                        <span className="text-muted-foreground text-xs"> / {teams.length}</span>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">
            &ldquo;Free picks&rdquo; = how many teams will be drafting normally in that round (not spending it on a keeper).
            Rounds highlighted in blue contain your keeper.
          </p>
        </div>
      )}

      {/* Teams without keepers entered */}
      {teamsWithoutKeepers.length > 0 && (
        <p className="text-xs text-muted-foreground">
          <span className="font-medium">{teamsWithoutKeepers.map(t => t.team_name).join(', ')}</span>
          {' '}— keepers not yet entered. Update{' '}
          <code className="bg-muted px-1 py-0.5 rounded">league_keepers.json</code> when you know.
        </p>
      )}
    </div>
  )
}

// ─── Keeper Rules Reference ───────────────────────────────────────────────────

function KeeperRulesPanel() {
  return (
    <div className="rounded-lg border bg-card p-5 space-y-4">
      <h3 className="font-semibold flex items-center gap-2">
        <Info className="h-4 w-4 text-muted-foreground" />
        Keeper Rules — California Palm League
      </h3>
      <div className="grid gap-3 sm:grid-cols-2 text-sm text-muted-foreground">
        <div className="space-y-1.5">
          <p className="font-medium text-foreground">Eligibility</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Max <strong>3 keepers</strong> per team</li>
            <li>Cannot keep 1st-round picks</li>
            <li>2nd-round picks: 2 years of control only</li>
            <li>Undrafted FAs: must be rostered before September call-ups</li>
          </ul>
        </div>
        <div className="space-y-1.5">
          <p className="font-medium text-foreground">Cost Calculation</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Drafted: <code className="bg-muted px-1 rounded">round − years_kept − 1</code></li>
            <li>Undrafted FAs: start at round 12, then move up</li>
            <li>Rounds 13+ are treated as round 12</li>
            <li>3-year maximum control window</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DraftPage() {
  const [myKeepers, setMyKeepers] = useState<MyKeeper[]>([])
  const [leagueData, setLeagueData] = useState<LeagueKeepersData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Draft date from league_settings or fallback
  // Sun Mar 22 7:30pm PDT = 2026-03-23T02:30:00Z
  const DRAFT_DATE = "2026-03-22T19:30:00-07:00"

  useEffect(() => {
    async function load() {
      try {
        const [keepersRes, leagueRes] = await Promise.all([
          fetch(`${BASE_PATH}/api/keepers.json`),
          fetch(`${BASE_PATH}/api/league_keepers.json`),
        ])

        const [keepersData, leagueJson] = await Promise.all([
          keepersRes.json(),
          leagueRes.json(),
        ])

        setMyKeepers(keepersData.keepers || [])
        setLeagueData(leagueJson)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load draft data.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const countdown = getDraftCountdown(DRAFT_DATE)

  const myTeam = leagueData?.teams.find(t => t.is_my_team)
  const myKeeperRounds = myKeepers.map(k => Number(k.round))
  // Picks I'm making by drafting (not using a keeper slot)
  const totalRounds = 24
  const myRealPickRounds = Array.from({ length: totalRounds }, (_, i) => i + 1).filter(
    r => !myKeeperRounds.includes(r)
  )

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <div className="h-8 w-48 bg-muted animate-pulse rounded mb-4" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-40 bg-muted animate-pulse rounded-xl" />
            ))}
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8 max-w-7xl space-y-8">

        {/* Header */}
        <header>
          <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
            <div className="flex items-center gap-3">
              <Link href="/">
                <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
                  <ArrowLeft className="h-4 w-4" />
                  Dashboard
                </Button>
              </Link>
              <div className="h-5 border-r" />
              <div>
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                  <Star className="h-7 w-7 text-amber-500" />
                  Draft Command Center
                </h1>
                <p className="text-muted-foreground text-sm mt-0.5">
                  {leagueData?.league_name} · {leagueData?.season ?? new Date().getFullYear()} Season
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link href="/draft/live">
                <Button size="sm" className="gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white">
                  <Zap className="h-3.5 w-3.5" />
                  Go Live
                </Button>
              </Link>
              <ThemeToggle />
            </div>
          </div>

          {/* Countdown Banner */}
          <div className={`rounded-xl border p-5 flex flex-wrap items-center justify-between gap-4 ${
            countdown.isPast && countdown.days === 0
              ? 'bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-900'
              : countdown.days <= 3 && !countdown.isPast
              ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900'
              : 'bg-card border'
          }`}>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1 flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                {countdown.isPast && countdown.days === 0
                  ? 'Draft is today!'
                  : countdown.isPast
                  ? 'Draft was'
                  : 'Draft in'
                }
              </div>
              <div className="text-4xl font-bold tracking-tight">
                {countdown.label}
              </div>
              <div className="text-sm text-muted-foreground mt-1">
                Sun Mar 22 · 7:30pm PDT · Snake draft, {totalRounds} rounds
              </div>
            </div>
            <div className="flex gap-6 text-center">
              <div>
                <div className="text-2xl font-bold text-primary">{myKeepers.length}</div>
                <div className="text-xs text-muted-foreground">My Keepers</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{totalRounds - myKeepers.length}</div>
                <div className="text-xs text-muted-foreground">Real Picks</div>
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {leagueData ? leagueData.teams.filter(t => t.keepers.length > 0).length : '—'}
                  <span className="text-muted-foreground text-lg">/{leagueData?.teams.length ?? '—'}</span>
                </div>
                <div className="text-xs text-muted-foreground">Teams Confirmed</div>
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {/* My Keepers — compact strip, hidden once draft is underway */}
        {!countdown.isPast && (
          <MyKeepersStrip keepers={myKeepers} keeperRounds={myKeeperRounds} />
        )}

        {/* League Keeper Board */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-600" />
              League Keeper Board
            </h2>
            {leagueData?.last_updated && (
              <span className="text-xs text-muted-foreground">
                Updated {leagueData.last_updated}
              </span>
            )}
          </div>

          {leagueData ? (
            <LeagueKeeperBoard teams={leagueData.teams} />
          ) : (
            <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
              <p>League keeper data unavailable.</p>
            </div>
          )}
        </section>

        {/* Keeper Rules Reference */}
        <section>
          <KeeperRulesPanel />
        </section>

        <footer className="text-center text-sm text-muted-foreground pb-4">
          <p>
            Update{" "}
            <code className="bg-muted px-1.5 py-0.5 rounded text-xs">public/api/league_keepers.json</code>
            {" "}as you learn other teams&apos; keepers.
          </p>
        </footer>
      </div>
    </main>
  )
}


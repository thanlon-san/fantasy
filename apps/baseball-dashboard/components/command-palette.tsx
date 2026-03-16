"use client"

import { useEffect, useState } from "react"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import { DialogProps } from "@radix-ui/react-dialog"

type RosterPlayer = {
  player: string
  position: string
  team: string
  confidence: number
  opponent: string
  tier?: "must-start" | "start" | "flex" | "bench" | "not-playing"
}

type WaiverPlayer = {
  player: string
  position: string
  team: string
  reason?: string
}

type BreakoutPlayer = {
  player: string
  position: string
  team: string
  signal?: string
  confidence?: number
}

interface CommandPaletteProps extends DialogProps {
  rosterPlayers?: RosterPlayer[]
  notPlayingPlayers?: { player: string; position: string; team: string }[]
  waiverPlayers?: WaiverPlayer[]
  breakoutPlayers?: BreakoutPlayer[]
  onSelectPlayer?: (player: RosterPlayer) => void
  /** @deprecated Use rosterPlayers instead */
  players?: RosterPlayer[]
}

export function CommandPalette({
  rosterPlayers,
  notPlayingPlayers = [],
  waiverPlayers = [],
  breakoutPlayers = [],
  onSelectPlayer,
  players,
  ...props
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false)

  // Support legacy `players` prop
  const activePlayers = rosterPlayers ?? players ?? []

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const hasActivePlayers = activePlayers.length > 0
  const hasNotPlaying = notPlayingPlayers.length > 0
  const hasWaiver = waiverPlayers.length > 0
  const hasBreakouts = breakoutPlayers.length > 0

  return (
    <CommandDialog open={open} onOpenChange={setOpen} {...props}>
      <CommandInput placeholder="Search players by name or team..." />
      <CommandList>
        <CommandEmpty>No players found.</CommandEmpty>

        {hasActivePlayers && (
          <CommandGroup heading="Active Roster">
            {activePlayers.map((player, index) => (
              <CommandItem
                key={`active-${player.player}-${index}`}
                value={`${player.player} ${player.team}`}
                onSelect={() => {
                  setOpen(false)
                  onSelectPlayer?.(player)
                }}
                className="flex justify-between"
              >
                <div className="flex flex-col">
                  <span className="font-medium">{player.player}</span>
                  <span className="text-xs text-muted-foreground">
                    {player.team} vs {player.opponent}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">
                    {player.position}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    player.confidence >= 80 ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' :
                    player.confidence >= 60 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400' :
                    'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
                  }`}>
                    {player.confidence}
                  </span>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {hasNotPlaying && (
          <>
            {hasActivePlayers && <CommandSeparator />}
            <CommandGroup heading="Not Playing Today">
              {notPlayingPlayers.map((player, index) => (
                <CommandItem
                  key={`bench-${player.player}-${index}`}
                  value={`${player.player} ${player.team}`}
                  className="flex justify-between"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{player.player}</span>
                    <span className="text-xs text-muted-foreground">{player.team} — no game today</span>
                  </div>
                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{player.position}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {hasWaiver && (
          <>
            {(hasActivePlayers || hasNotPlaying) && <CommandSeparator />}
            <CommandGroup heading="Waiver Targets">
              {waiverPlayers.map((player, index) => (
                <CommandItem
                  key={`waiver-${player.player}-${index}`}
                  value={`${player.player} ${player.team}`}
                  className="flex justify-between"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{player.player}</span>
                    <span className="text-xs text-muted-foreground truncate max-w-[260px]">{player.reason || player.team}</span>
                  </div>
                  <span className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400 px-1.5 py-0.5 rounded">
                    {player.position}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {hasBreakouts && (
          <>
            {(hasActivePlayers || hasNotPlaying || hasWaiver) && <CommandSeparator />}
            <CommandGroup heading="Breakout Alerts">
              {breakoutPlayers.map((player, index) => (
                <CommandItem
                  key={`breakout-${player.player}-${index}`}
                  value={`${player.player} ${player.team}`}
                  className="flex justify-between"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{player.player}</span>
                    <span className="text-xs text-muted-foreground">{player.team} — {player.signal ?? 'Breakout'}</span>
                  </div>
                  <span className="text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400 px-1.5 py-0.5 rounded">
                    {player.position}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  )
}

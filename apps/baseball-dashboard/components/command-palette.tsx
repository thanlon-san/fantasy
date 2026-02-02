"use client"

import { useEffect, useState } from "react"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { DialogProps } from "@radix-ui/react-dialog"

type Player = {
  player: string
  position: string
  team: string
  confidence: number
  opponent: string
}

interface CommandPaletteProps extends DialogProps {
  players: Player[]
  onSelectPlayer?: (player: Player) => void
}

export function CommandPalette({ players, onSelectPlayer, ...props }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)

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

  return (
    <CommandDialog open={open} onOpenChange={setOpen} {...props}>
      <CommandInput placeholder="Search players by name or team..." />
      <CommandList>
        <CommandEmpty>No players found.</CommandEmpty>
        <CommandGroup heading="Roster">
          {players.map((player, index) => (
            <CommandItem
              key={`${player.player}-${index}`}
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
                  player.confidence >= 80 ? 'bg-green-100 text-green-700' :
                  player.confidence >= 60 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {player.confidence}
                </span>
              </div>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}

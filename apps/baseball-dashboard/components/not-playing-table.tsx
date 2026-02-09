"use client"

import { useState, useMemo } from "react"
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
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react"

type NotPlayingPlayer = {
  player: string
  position: string
  team: string
  adp?: number
}

type SortKey = "player" | "position" | "team" | "adp"
type SortDirection = "asc" | "desc" | null

interface NotPlayingTableProps {
  players: NotPlayingPlayer[]
}

export function NotPlayingTable({ players }: NotPlayingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      if (sortDirection === "asc") {
        setSortDirection("desc")
      } else if (sortDirection === "desc") {
        setSortKey(null)
        setSortDirection(null)
      } else {
        setSortDirection("asc")
      }
    } else {
      setSortKey(key)
      setSortDirection("asc")
    }
  }

  const sortedPlayers = useMemo(() => {
    if (!sortKey || !sortDirection) return players

    return [...players].sort((a, b) => {
      let aVal: string | number | undefined = a[sortKey]
      let bVal: string | number | undefined = b[sortKey]

      // Handle undefined ADPs
      if (sortKey === "adp") {
        if (aVal === undefined) return 1
        if (bVal === undefined) return -1
      }

      if (typeof aVal === "string") {
        aVal = aVal.toLowerCase()
        bVal = (bVal as string).toLowerCase()
      }

      if (sortDirection === "asc") {
        return aVal! > bVal! ? 1 : -1
      } else {
        return aVal! < bVal! ? 1 : -1
      }
    })
  }, [players, sortKey, sortDirection])

  const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
    if (sortKey !== columnKey) {
      return <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="ml-1 h-3 w-3" />
    }
    return <ArrowDown className="ml-1 h-3 w-3" />
  }

  if (players.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>All players are playing today!</p>
      </div>
    )
  }

  return (
    <div className="rounded-md border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="border-b bg-muted/50">
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("player")}
              >
                Player
                <SortIcon columnKey="player" />
              </Button>
            </TableHead>
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("position")}
              >
                Position
                <SortIcon columnKey="position" />
              </Button>
            </TableHead>
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("team")}
              >
                Team
                <SortIcon columnKey="team" />
              </Button>
            </TableHead>
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("adp")}
              >
                ADP
                <SortIcon columnKey="adp" />
              </Button>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedPlayers.map((player, i) => (
            <TableRow key={i} className="bg-muted/30">
              <TableCell className="font-medium">{player.player}</TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs">
                  {player.position}
                </Badge>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {player.team}
              </TableCell>
              <TableCell className="text-sm">
                {player.adp ? (
                  <Badge variant="secondary">{Math.round(player.adp)}</Badge>
                ) : (
                  <span className="text-muted-foreground text-xs">N/A</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

"use client"

import { useState, useMemo } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown, 
  MoreHorizontal, 
  ClipboardCopy, 
  BarChart2, 
  Eye
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { PlayerDetailDialog } from "@/components/player-detail-dialog"
import { useToast } from "@/components/ui/use-toast"

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

type Player = {
  player: string
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

type SortKey = "player" | "position" | "confidence" | "matchup" | "opponent"
type SortDirection = "asc" | "desc" | null

interface PlayerTableProps {
  players: Player[]
  variant?: "must-start" | "start" | "flex" | "bench" | "default"
  showAllColumns?: boolean
}

export function PlayerTable({ players, variant = "default", showAllColumns = true }: PlayerTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const { toast } = useToast()

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
      let aVal: string | number = a[sortKey]
      let bVal: string | number = b[sortKey]

      if (typeof aVal === "string") {
        aVal = aVal.toLowerCase()
        bVal = (bVal as string).toLowerCase()
      }

      if (sortDirection === "asc") {
        return aVal > bVal ? 1 : -1
      } else {
        return aVal < bVal ? 1 : -1
      }
    })
  }, [players, sortKey, sortDirection])

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return "bg-green-600 hover:bg-green-700"
    if (confidence >= 60) return "bg-yellow-600 hover:bg-yellow-700"
    return "bg-red-600 hover:bg-red-700"
  }

  const getRowVariant = () => {
    switch (variant) {
      case "must-start":
        return "bg-green-50/50 dark:bg-green-950/20 hover:bg-green-100/50 dark:hover:bg-green-950/30"
      case "bench":
        return "bg-yellow-50/50 dark:bg-yellow-950/20 hover:bg-yellow-100/50 dark:hover:bg-yellow-950/30"
      default:
        return "hover:bg-muted/50"
    }
  }

  const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
    if (sortKey !== columnKey) {
      return <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="ml-1 h-3 w-3" />
    }
    return <ArrowDown className="ml-1 h-3 w-3" />
  }

  const handleCopyPlayer = (player: Player) => {
    navigator.clipboard.writeText(`${player.player} (${player.position}) - ${player.confidence}% Confidence`)
    toast({
      title: "Copied to clipboard",
      description: `${player.player} details copied.`,
    })
  }

  if (players.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No players in this category</p>
      </div>
    )
  }

  return (
    <div className="rounded-md border bg-card shadow-sm">
      <TooltipProvider>
      <Table>
        <TableHeader>
          <TableRow className="border-b bg-muted/50">
            <TableHead className="w-[180px]">
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
            <TableHead className="w-[100px]">
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
            <TableHead className="w-[120px]">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("opponent")}
              >
                Matchup
                <SortIcon columnKey="opponent" />
              </Button>
            </TableHead>
            <TableHead className="w-[150px] hidden md:table-cell">Pitcher</TableHead>
            <TableHead className="w-[120px]">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 font-medium"
                onClick={() => handleSort("confidence")}
              >
                Confidence
                <SortIcon columnKey="confidence" />
              </Button>
            </TableHead>
            {showAllColumns && (
              <>
                <TableHead className="w-[100px] hidden lg:table-cell">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 font-medium"
                        onClick={() => handleSort("matchup")}
                      >
                        Matchup
                        <SortIcon columnKey="matchup" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Hitter vs Pitcher historical & projected performance</p>
                    </TooltipContent>
                  </Tooltip>
                </TableHead>
                <TableHead className="w-[80px] hidden lg:table-cell">
                  <Tooltip>
                    <TooltipTrigger className="cursor-help">Park</TooltipTrigger>
                    <TooltipContent><p>Park Factor (100 = Neutral)</p></TooltipContent>
                  </Tooltip>
                </TableHead>
                <TableHead className="w-[80px] hidden xl:table-cell">
                  <Tooltip>
                    <TooltipTrigger className="cursor-help">Form</TooltipTrigger>
                    <TooltipContent><p>Recent performance rating</p></TooltipContent>
                  </Tooltip>
                </TableHead>
                <TableHead className="w-[80px] hidden xl:table-cell">
                  <Tooltip>
                    <TooltipTrigger className="cursor-help">Platoon</TooltipTrigger>
                    <TooltipContent><p>Handedness Advantage</p></TooltipContent>
                  </Tooltip>
                </TableHead>
              </>
            )}
            <TableHead className="min-w-[200px]">Reasons</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedPlayers.map((player, i) => (
            <TableRow 
              key={i} 
              className={`cursor-pointer group ${getRowVariant()}`}
              onClick={() => {
                setSelectedPlayer(player)
                setDialogOpen(true)
              }}
            >
              <TableCell className="font-semibold">
                <div className="flex flex-col">
                  <span>{player.player}</span>
                  <span className="text-xs text-muted-foreground md:hidden">{player.team}</span>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs">
                  {player.position}
                </Badge>
              </TableCell>
              <TableCell className="text-sm">
                <div className="flex flex-col">
                  <span className="font-medium">{player.opponent}</span>
                  <span className="text-xs text-muted-foreground">{player.team}</span>
                </div>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground hidden md:table-cell">
                {player.opponent_pitcher || "TBD"}
              </TableCell>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <div className="flex flex-col gap-1 group/badge">
                  <Badge className={`${getConfidenceColor(player.confidence)} w-12 justify-center transition-transform group-hover/badge:scale-105`}>
                    {player.confidence}
                  </Badge>
                </div>
              </TableCell>
              {showAllColumns && (
                <>
                  <TableCell className="hidden lg:table-cell">
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-medium">{player.matchup}</span>
                      <Progress value={player.matchup} className="h-1 w-12" />
                    </div>
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">{player.parkFactor}</span>
                    </div>
                  </TableCell>
                  <TableCell className="hidden xl:table-cell">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">{player.form}</span>
                    </div>
                  </TableCell>
                  <TableCell className="hidden xl:table-cell">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">{player.platoon}</span>
                    </div>
                  </TableCell>
                </>
              )}
              <TableCell className="text-sm text-muted-foreground">
                <div className="flex flex-wrap gap-1.5 max-w-md">
                  {player.reasons.map((reason, idx) => (
                    <span
                      key={idx}
                      className="inline-block bg-muted px-2 py-1 rounded text-sm"
                    >
                      {reason}
                    </span>
                  ))}
                </div>
              </TableCell>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuItem onClick={() => {
                      setSelectedPlayer(player)
                      setDialogOpen(true)
                    }}>
                      <Eye className="mr-2 h-4 w-4" /> View Details
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleCopyPlayer(player)}>
                      <ClipboardCopy className="mr-2 h-4 w-4" /> Copy Name
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => {
                      // Placeholder for future feature
                      toast({ title: "Compare", description: "Comparison feature coming soon" })
                    }}>
                      <BarChart2 className="mr-2 h-4 w-4" /> Compare
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      </TooltipProvider>
      
      <PlayerDetailDialog 
        player={selectedPlayer} 
        open={dialogOpen} 
        onOpenChange={setDialogOpen} 
      />
    </div>
  )
}

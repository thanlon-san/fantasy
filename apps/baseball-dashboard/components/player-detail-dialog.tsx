"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TrendingUp, User, MapPin, Shield } from "lucide-react"

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

interface PlayerDetailDialogProps {
  player: Player | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PlayerDetailDialog({ player, open, onOpenChange }: PlayerDetailDialogProps) {
  if (!player) return null

  const getConfidenceColor = (val: number) => {
    if (val >= 80) return "text-green-600"
    if (val >= 60) return "text-yellow-600"
    return "text-red-600"
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="text-2xl flex items-center gap-2">
                {player.player}
                <Badge variant="outline" className="text-base font-normal">
                  {player.position}
                </Badge>
              </DialogTitle>
              <DialogDescription className="text-base mt-1">
                {player.team} vs {player.opponent} • {player.game_time || "Time TBD"}
              </DialogDescription>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${getConfidenceColor(player.confidence)}`}>
                {player.confidence}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">Confidence</div>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="analysis">Detailed Analysis</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-6 pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-muted/50 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-muted-foreground mb-2">
                  <User className="h-4 w-4" />
                  <span className="text-sm font-medium">Opposing Pitcher</span>
                </div>
                <div className="text-lg font-semibold">{player.opponent_pitcher || "TBD"}</div>
              </div>
              
              <div className="p-4 bg-muted/50 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-muted-foreground mb-2">
                  <MapPin className="h-4 w-4" />
                  <span className="text-sm font-medium">Park Factors</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-semibold">{player.parkFactor}</span>
                  <Progress value={player.parkFactor} className="h-2 w-20" />
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold mb-3">Key Factors</h4>
              <div className="flex flex-wrap gap-2">
                {player.reasons.map((reason, i) => (
                  <Badge key={i} variant="secondary" className="text-sm py-1">
                    {reason}
                  </Badge>
                ))}
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="analysis" className="space-y-6 pt-4">
            <div className="space-y-4">
              <div className="grid gap-4">
                <div className="grid grid-cols-12 items-center gap-4">
                  <div className="col-span-4 text-sm font-medium flex items-center gap-2">
                    <Shield className="h-4 w-4 text-blue-500" /> Matchup Quality
                  </div>
                  <div className="col-span-6">
                    <Progress value={player.matchup} className="h-2" />
                  </div>
                  <div className="col-span-2 text-right font-bold">{player.matchup}</div>
                </div>

                <div className="grid grid-cols-12 items-center gap-4">
                  <div className="col-span-4 text-sm font-medium flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-orange-500" /> Recent Form
                  </div>
                  <div className="col-span-6">
                    <Progress value={player.form} className="h-2" />
                  </div>
                  <div className="col-span-2 text-right font-bold">{player.form}</div>
                </div>

                <div className="grid grid-cols-12 items-center gap-4">
                  <div className="col-span-4 text-sm font-medium flex items-center gap-2">
                    <User className="h-4 w-4 text-purple-500" /> Platoon Adv.
                  </div>
                  <div className="col-span-6">
                    <Progress value={player.platoon} className="h-2" />
                  </div>
                  <div className="col-span-2 text-right font-bold">{player.platoon}</div>
                </div>
              </div>

              <div className="mt-6 p-4 border rounded-md bg-card">
                <h4 className="font-semibold mb-2 text-sm text-muted-foreground">AI Analysis</h4>
                <p className="text-sm leading-relaxed">
                  {player.player} has a <strong>{player.confidence}% confidence rating</strong> today. 
                  The matchup against {player.opponent_pitcher || "the opposing pitcher"} is rated {player.matchup}/100.
                  {player.parkFactor > 50 ? " The park factors are favorable." : " The park factors are neutral or unfavorable."}
                  {player.form > 70 && " The player is currently in excellent form."}
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

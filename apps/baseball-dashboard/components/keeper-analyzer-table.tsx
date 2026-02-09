"use client"

import { Badge } from "@/components/ui/badge"
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Star } from "lucide-react"

export type KeeperRecommendation = {
  player: string
  round: string
  adp: number
  value: string
  surplus: string
}

interface KeeperAnalyzerTableProps {
  recommendations: KeeperRecommendation[]
}

export function KeeperAnalyzerTable({ recommendations }: KeeperAnalyzerTableProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Star className="h-5 w-5 text-emerald-600" />
          Keepers
        </h2>
        <Badge variant="secondary">{recommendations.length}</Badge>
      </div>

      <div className="rounded-md border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="px-5 py-4">Player</TableHead>
              <TableHead className="px-5 py-4 text-center">Round</TableHead>
              <TableHead className="px-5 py-4 text-center">ADP</TableHead>
              <TableHead className="px-5 py-4 text-right">Value</TableHead>
              <TableHead className="px-5 py-4 text-right">Surplus</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recommendations.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="px-5 py-8 text-center text-muted-foreground">
                  No keeper data
                </TableCell>
              </TableRow>
            ) : (
              recommendations.map((keeper, i) => (
                <TableRow key={i}>
                  <TableCell className="px-5 py-4">
                    <div className="font-semibold">{keeper.player}</div>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-center">
                    <Badge variant="secondary" className="font-mono">{keeper.round}</Badge>
                  </TableCell>
                  <TableCell className="px-5 py-4 text-center text-muted-foreground">
                    {keeper.adp}
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right text-muted-foreground">
                    {keeper.value}
                  </TableCell>
                  <TableCell className="px-5 py-4 text-right">
                    <span className="font-bold text-emerald-600">{keeper.surplus}</span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

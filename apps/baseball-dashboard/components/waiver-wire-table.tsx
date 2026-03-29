"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Target, TrendingUp, Calendar, ArrowRight, Flame, MapPin } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { WaiverTarget } from "@fantasy/types"

interface WaiverWireTableProps {
  targets: WaiverTarget[]
}

export function WaiverWireTable({ targets }: WaiverWireTableProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Target className="h-5 w-5 text-purple-600" />
          Waiver Wire
        </h2>
        <Badge variant="secondary">{targets.length} targets</Badge>
      </div>

      {targets.length === 0 ? (
        <div className="rounded-md border bg-card p-8 text-center text-muted-foreground">
          No waiver recommendations
        </div>
      ) : (
        <div className="space-y-4">
          {targets.map((target, i) => {
            const isHitter = target.position !== "SP" && target.position !== "RP"
            
            return (
              <div 
                key={i} 
                className="rounded-lg border bg-card hover:bg-accent/50 transition-colors overflow-hidden"
              >
                {/* Header Section */}
                <div className="p-4 border-b bg-muted/20">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <Link href={`/player?name=${encodeURIComponent(target.player)}`} className="font-bold text-lg hover:underline">{target.player}</Link>
                          {target.trending === "HOT" && (
                            <Badge variant="default" className="bg-orange-500 hover:bg-orange-600 border-none text-white gap-1">
                              <Flame className="h-3 w-3" /> Hot
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {target.position} • {target.team}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {target.rostered_pct !== undefined && (
                        <div className="text-right">
                          <div className="text-sm font-medium">{target.rostered_pct}%</div>
                          <div className="text-xs text-muted-foreground">Rostered</div>
                        </div>
                      )}
                      {target.confidence && (
                        <div className="text-right">
                          <div className={`text-2xl font-bold ${
                            target.confidence === "STRONG" ? "text-purple-600" : "text-purple-500"
                          }`}>
                            {target.confidence === "STRONG" ? "90" : 
                             target.confidence === "MODERATE" ? "70" : "50"}%
                          </div>
                          <div className="text-xs text-muted-foreground">confidence</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Content Grid */}
                <div className="grid md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x">
                  {/* Left Column: Stats Comparison */}
                  <div className="p-4 space-y-4">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Performance Trends
                    </div>
                    
                    {target.last_7_days ? (
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent border-none">
                            <TableHead className="h-8 pl-0">Metric</TableHead>
                            <TableHead className="h-8 text-right">Last 7d</TableHead>
                            <TableHead className="h-8 text-right">Last 14d</TableHead>
                            <TableHead className="h-8 text-right">Last 30d</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {isHitter ? (
                            <>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">AVG</TableCell>
                                <TableCell className="py-1 text-right">.{Math.round((target.last_7_days.avg || 0) * 1000)}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? `.${Math.round((target.last_14_days.avg || 0) * 1000)}` : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? `.${Math.round((target.last_30_days.avg || 0) * 1000)}` : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">OPS</TableCell>
                                <TableCell className="py-1 text-right">{(target.last_7_days.ops || 0).toFixed(3)}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days?.ops != null ? target.last_14_days.ops.toFixed(3) : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days?.ops != null ? target.last_30_days.ops.toFixed(3) : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">HR</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.hr || 0}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? target.last_14_days.hr || 0 : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? target.last_30_days.hr || 0 : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">RBI</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.rbi || 0}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? target.last_14_days.rbi || 0 : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? target.last_30_days.rbi || 0 : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">SB</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.sb || 0}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? target.last_14_days.sb || 0 : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? target.last_30_days.sb || 0 : '-'}
                                </TableCell>
                              </TableRow>
                            </>
                          ) : (
                            <>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">ERA</TableCell>
                                <TableCell className="py-1 text-right">{(target.last_7_days.era || 0).toFixed(2)}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? (target.last_14_days.era || 0).toFixed(2) : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? (target.last_30_days.era || 0).toFixed(2) : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">WHIP</TableCell>
                                <TableCell className="py-1 text-right">{(target.last_7_days.whip || 0).toFixed(2)}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? (target.last_14_days.whip || 0).toFixed(2) : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? (target.last_30_days.whip || 0).toFixed(2) : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">K</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.k || 0}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? target.last_14_days.k || 0 : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? target.last_30_days.k || 0 : '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">IP</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.ip ?? '-'}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days?.ip ?? '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days?.ip ?? '-'}
                                </TableCell>
                              </TableRow>
                              <TableRow className="hover:bg-transparent border-none">
                                <TableCell className="py-1 pl-0 font-medium">SV</TableCell>
                                <TableCell className="py-1 text-right">{target.last_7_days.sv || 0}</TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_14_days ? target.last_14_days.sv || 0 : '-'}
                                </TableCell>
                                <TableCell className="py-1 text-right text-muted-foreground">
                                  {target.last_30_days ? target.last_30_days.sv || 0 : '-'}
                                </TableCell>
                              </TableRow>
                            </>
                          )}
                        </TableBody>
                      </Table>
                    ) : (
                      <div className="text-sm text-muted-foreground py-2">Off-season data unavailable</div>
                    )}
                  </div>

                  {/* Right Column: Context & Statcast */}
                  <div className="p-4 space-y-6">
                    {/* Statcast */}
                    {target.statcast_changes && (
                      <div className="space-y-3">
                        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                          <TrendingUp className="h-3 w-3" />
                          Statcast Changes
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          {Object.entries(target.statcast_changes).map(([key, value]) => {
                            const isPositive = !String(value).trimStart().startsWith('-')
                            return (
                              <div key={key} className="bg-muted/30 p-2 rounded text-center">
                                <div className="text-[10px] text-muted-foreground uppercase mb-1">
                                  {key.replace(/_/g, ' ')}
                                </div>
                                <div className={`text-sm font-semibold ${isPositive ? 'text-green-600' : 'text-red-500'}`}>
                                  {value}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}

                    {/* Opportunity / Reason */}
                    <div className="space-y-3">
                      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        Outlook
                      </div>
                      <div className="space-y-2 text-sm">
                        {target.role_change && (
                          <div className="flex items-start gap-2">
                            <MapPin className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                            <span>{target.role_change}</span>
                          </div>
                        )}
                        {target.upcoming_schedule && (
                          <div className="flex items-start gap-2">
                            <Calendar className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                            <span>{target.upcoming_schedule}</span>
                          </div>
                        )}
                        {!target.role_change && !target.upcoming_schedule && (
                          <div className="flex items-start gap-2">
                            <ArrowRight className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                            <span className="text-muted-foreground">{target.reason}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

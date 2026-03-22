"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { ArrowLeft, RefreshCw, Shield, AlertTriangle, CheckCircle2, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"

const API_BASE = process.env.NEXT_PUBLIC_DRAFT_API_URL ?? "http://localhost:8001"

type Closer = {
  name:       string
  team:       string
  position:   string
  is_keeper:  boolean
  saves:      number | null
  era:        number | null
  whip:       number | null
  k:          number | null
  hr_allowed: number | null
}

function statCell(val: number | null, name: string, isGood?: boolean): { text: string; color: string } {
  if (val === null || val === undefined) return { text: "–", color: "text-slate-500" }
  let text = ""
  if (name === "ERA" || name === "WHIP") text = val.toFixed(2)
  else text = val.toString()

  let color = "text-slate-300"
  if (isGood !== undefined) {
    color = isGood ? "text-emerald-400" : "text-slate-300"
  }
  return { text, color }
}

function eraColor(era: number | null): string {
  if (era === null) return "text-slate-500"
  if (era < 2.5)  return "text-emerald-400"
  if (era < 3.5)  return "text-sky-400"
  if (era < 4.5)  return "text-amber-400"
  return "text-red-400"
}

function whipColor(whip: number | null): string {
  if (whip === null) return "text-slate-500"
  if (whip < 1.0)  return "text-emerald-400"
  if (whip < 1.2)  return "text-sky-400"
  if (whip < 1.35) return "text-amber-400"
  return "text-red-400"
}

export default function ClosersPage() {
  const [closers,    setClosers]    = useState<Closer[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetch_ = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const res = await fetch(`${API_BASE}/season/closers`, { cache: "no-store" })
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data = await res.json()
      setClosers(data.closers ?? [])
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach server")
    } finally {
      setLoading(false)
      if (showRefresh) setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetch_()
    const t = setInterval(() => fetch_(), 120_000)
    return () => clearInterval(t)
  }, [fetch_])

  if (loading) return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-500 animate-pulse text-sm">Loading closer data…</div>
    </main>
  )

  if (error) return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-slate-600 mx-auto" />
        <div className="text-slate-400">{error}</div>
        <div className="text-slate-600 text-xs font-mono">python scripts/draft_server.py</div>
        <Button size="sm" variant="outline" onClick={() => fetch_(true)}>Retry</Button>
      </div>
    </main>
  )

  const hasStats = closers.some(c => c.saves !== null || c.era !== null)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/"><Button variant="ghost" size="sm" className="text-slate-500 gap-1.5"><ArrowLeft className="h-4 w-4" />Dashboard</Button></Link>
            <div className="h-4 border-r border-slate-700" />
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-purple-400" />
              <span className="font-bold text-lg">Closer Monitor</span>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => fetch_(true)} disabled={refreshing}>
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Strategy callout */}
        <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 px-5 py-4 space-y-2">
          <div className="text-sm font-bold text-purple-300">Your Pitching Strategy</div>
          <p className="text-xs text-slate-400 leading-relaxed">
            You&apos;re stacking closers to dominate <strong className="text-slate-200">HR Allowed, ERA, WHIP, and SV</strong> — 4 of 6 pitching categories every week. Closer role security is critical. Monitor this page weekly for blown saves, role changes, and ERA spikes.
          </p>
        </div>

        {!hasStats && (
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-3 text-center text-sm text-slate-400">
            Season starts March 25 — live stats will appear once games are played.
          </div>
        )}

        {/* Closer cards */}
        <div className="space-y-4">
          {closers.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-8">
              No relievers found on your roster yet. Add closers in the draft tonight!
            </div>
          )}
          {closers.map((c, i) => (
            <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-900/60 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/40">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-lg text-slate-100">{c.name}</span>
                    {c.is_keeper && (
                      <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        <Lock className="h-2.5 w-2.5" /> KEEPER
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-slate-400 mt-0.5">{c.position} · {c.team}</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-black text-purple-400">{c.saves ?? "–"}</div>
                  <div className="text-xs text-slate-500">Saves</div>
                </div>
              </div>

              <div className="grid grid-cols-4 divide-x divide-slate-700/40 px-0">
                {[
                  { label: "ERA",  val: c.era,        color: eraColor(c.era)    },
                  { label: "WHIP", val: c.whip,       color: whipColor(c.whip)  },
                  { label: "K",    val: c.k,          color: "text-slate-300"   },
                  { label: "HR",   val: c.hr_allowed, color: c.hr_allowed !== null ? (c.hr_allowed <= 3 ? "text-emerald-400" : c.hr_allowed <= 6 ? "text-amber-400" : "text-red-400") : "text-slate-500" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="text-center py-3">
                    <div className={`text-base font-bold font-mono ${color}`}>
                      {val !== null && val !== undefined
                        ? (label === "ERA" || label === "WHIP" ? val.toFixed(2) : val.toString())
                        : "–"
                      }
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
                  </div>
                ))}
              </div>

              {/* Role status row */}
              <div className="px-5 py-2.5 border-t border-slate-700/40 flex items-center gap-2 text-xs text-slate-400">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                <span>Closer role confirmed pre-season</span>
                <span className="ml-auto text-slate-600">Check for role news weekly</span>
              </div>
            </div>
          ))}
        </div>

        {/* What to watch */}
        <div className="rounded-xl border border-slate-700/40 bg-slate-900/40 p-5 space-y-3">
          <div className="text-sm font-bold text-slate-300">What to watch each week</div>
          <ul className="space-y-2 text-xs text-slate-400">
            <li className="flex items-start gap-2"><span className="text-red-400 shrink-0">▸</span> <span><strong className="text-slate-300">Blown saves</strong> — 2+ in a week signals role risk. Check beat reporters.</span></li>
            <li className="flex items-start gap-2"><span className="text-amber-400 shrink-0">▸</span> <span><strong className="text-slate-300">ERA spike</strong> (&gt;4.00 over 3+ weeks) — consider streaming a replacement to protect your ERA category.</span></li>
            <li className="flex items-start gap-2"><span className="text-sky-400 shrink-0">▸</span> <span><strong className="text-slate-300">Injury reports</strong> — a closer IL trip opens a streaming opportunity; pick up the handcuff immediately.</span></li>
            <li className="flex items-start gap-2"><span className="text-purple-400 shrink-0">▸</span> <span><strong className="text-slate-300">Save opportunities</strong> — teams with big leads generate more save chances. Track your closers&apos; team W-L record.</span></li>
          </ul>
        </div>

        <footer className="text-center text-xs text-slate-600 pb-4">Updated every 2min from Yahoo</footer>
      </div>
    </main>
  )
}

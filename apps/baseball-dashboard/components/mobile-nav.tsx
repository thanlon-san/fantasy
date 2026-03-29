"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Home, Swords, Trophy, Radio, ArrowRightLeft,
  BarChart3, CalendarRange, DollarSign, Shield,
  TrendingUp, Sparkles,
} from "lucide-react"

const NAV_ITEMS = [
  { href: "/",            label: "Home",       icon: Home },
  { href: "/matchup",     label: "Matchup",    icon: Swords },
  { href: "/trade",       label: "Trade",      icon: ArrowRightLeft },
  { href: "/streamers",   label: "Streamers",  icon: Radio },
  { href: "/prospects",   label: "Prospects",  icon: Sparkles },
]

const MORE_ITEMS = [
  { href: "/standings",   label: "Standings",   icon: Trophy },
  { href: "/closers",     label: "Closers",     icon: Shield },
  { href: "/trajectory",  label: "Trajectory",  icon: TrendingUp },
  { href: "/regression",  label: "Regression",  icon: BarChart3 },
  { href: "/projections", label: "Projections", icon: DollarSign },
  { href: "/planner",     label: "Planner",     icon: CalendarRange },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 inset-x-0 z-50 bg-slate-950/95 backdrop-blur border-t border-slate-800 md:hidden safe-area-bottom">
      <div className="flex items-center justify-around h-14 px-1">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center justify-center flex-1 h-full gap-0.5 min-w-0 touch-manipulation ${
                isActive
                  ? "text-emerald-400"
                  : "text-slate-500 active:text-slate-300"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="text-[10px] font-medium leading-none truncate">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export function MobileMoreDrawer() {
  const pathname = usePathname()

  return (
    <div className="grid grid-cols-3 gap-2 p-4 md:hidden">
      {MORE_ITEMS.map(item => {
        const Icon = item.icon
        const isActive = pathname === item.href
        return (
          <Link
            key={item.href + item.label}
            href={item.href}
            className={`flex flex-col items-center justify-center rounded-lg border p-3 gap-1.5 touch-manipulation ${
              isActive
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                : "border-slate-700/60 bg-slate-900/40 text-slate-400 active:bg-slate-800"
            }`}
          >
            <Icon className="h-5 w-5" />
            <span className="text-xs font-medium">{item.label}</span>
          </Link>
        )
      })}
    </div>
  )
}

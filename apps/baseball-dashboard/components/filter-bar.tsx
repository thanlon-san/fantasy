"use client"

import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { Search, X, Filter, RotateCcw } from "lucide-react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

interface FilterBarProps {
  searchTerm: string
  onSearchChange: (value: string) => void
  positionFilter: string
  onPositionFilterChange: (value: string) => void
  confidenceThreshold: number
  onConfidenceThresholdChange: (value: number) => void
  onClearFilters: () => void
  playerCount: number
}

export function FilterBar({
  searchTerm,
  onSearchChange,
  positionFilter,
  onPositionFilterChange,
  confidenceThreshold,
  onConfidenceThresholdChange,
  onClearFilters,
  playerCount
}: FilterBarProps) {
  const activeFiltersCount = [
    searchTerm !== "",
    positionFilter !== "all",
    confidenceThreshold > 0
  ].filter(Boolean).length

  return (
    <div className="flex flex-col gap-4 mb-6 p-4 bg-card rounded-lg border shadow-sm">
      <div className="flex flex-col md:flex-row gap-4 items-center">
        <div className="relative w-full md:w-72">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search players..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
          {searchTerm && (
            <button 
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <Select value={positionFilter} onValueChange={onPositionFilterChange}>
          <SelectTrigger className="w-full md:w-[180px]">
            <SelectValue placeholder="Position" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Positions</SelectItem>
            <SelectItem value="C">Catcher</SelectItem>
            <SelectItem value="1B">First Base</SelectItem>
            <SelectItem value="2B">Second Base</SelectItem>
            <SelectItem value="3B">Third Base</SelectItem>
            <SelectItem value="SS">Shortstop</SelectItem>
            <SelectItem value="OF">Outfield</SelectItem>
            <SelectItem value="DH">Designated Hitter</SelectItem>
            <SelectItem value="SP">Starting Pitcher</SelectItem>
            <SelectItem value="RP">Relief Pitcher</SelectItem>
          </SelectContent>
        </Select>

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="w-full md:w-auto gap-2">
              <Filter className="h-4 w-4" />
              Filters
              {confidenceThreshold > 0 && (
                <Badge variant="secondary" className="ml-1 px-1 h-5 text-xs">
                  {confidenceThreshold}+
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="space-y-4">
              <h4 className="font-medium leading-none">Confidence Threshold</h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Min Confidence</Label>
                  <span className="text-sm text-muted-foreground">{confidenceThreshold}</span>
                </div>
                <Slider
                  value={[confidenceThreshold]}
                  onValueChange={(vals) => onConfidenceThresholdChange(vals[0])}
                  min={0}
                  max={100}
                  step={5}
                />
                <p className="text-xs text-muted-foreground">
                  Only show players with confidence score above {confidenceThreshold}
                </p>
              </div>
            </div>
          </PopoverContent>
        </Popover>

        {activeFiltersCount > 0 && (
          <Button 
            variant="ghost" 
            onClick={onClearFilters}
            className="w-full md:w-auto gap-2 ml-auto md:ml-0"
          >
            <RotateCcw className="h-4 w-4" />
            Clear
          </Button>
        )}
        
        <div className="ml-auto text-sm text-muted-foreground hidden md:block">
          Showing {playerCount} players
        </div>
      </div>
    </div>
  )
}

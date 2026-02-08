"use client";

import {
  CalendarIcon,
  CarIcon,
  ClockIcon,
  StickyNoteIcon,
  StarIcon,
  TrophyIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ResultItem } from "@/lib/types/booking";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ProviderCardProps {
  result: ResultItem;
  onSelect?: (result: ResultItem) => void;
}

const RANK_STYLES: Record<number, { bg: string; text: string; label: string }> =
  {
    1: {
      bg: "bg-amber-100 dark:bg-amber-900/30",
      text: "text-amber-700 dark:text-amber-400",
      label: "Best Match",
    },
    2: {
      bg: "bg-slate-100 dark:bg-slate-800/50",
      text: "text-slate-600 dark:text-slate-300",
      label: "2nd",
    },
    3: {
      bg: "bg-orange-100 dark:bg-orange-900/30",
      text: "text-orange-700 dark:text-orange-400",
      label: "3rd",
    },
  };

function formatSlot(slot: string): { date: string; time: string } {
  const d = new Date(slot);
  const date = d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return { date, time };
}

export function ProviderCard({ result, onSelect }: ProviderCardProps) {
  const rankStyle = RANK_STYLES[result.rank];
  const isTop = result.rank === 1;
  const { date, time } = formatSlot(result.slot);

  return (
    <Card
      className={cn(
        "transition-shadow hover:shadow-md",
        isTop && "ring-2 ring-primary/20",
      )}
    >
      <CardContent className="pt-5">
        <div className="flex items-start justify-between gap-3">
          {/* Left: provider info */}
          <div className="min-w-0 flex-1 space-y-2.5">
            {/* Rank + Name */}
            <div className="flex items-center gap-2">
              {rankStyle ? (
                <Badge
                  variant="secondary"
                  className={cn(
                    "gap-1 text-[11px]",
                    rankStyle.bg,
                    rankStyle.text,
                  )}
                >
                  <TrophyIcon className="size-3" />
                  {rankStyle.label}
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[11px]">
                  #{result.rank}
                </Badge>
              )}
              <span className="text-xs tabular-nums text-muted-foreground">
                {(result.score * 100).toFixed(0)}%
              </span>
            </div>

            <h3 className="text-sm font-semibold leading-tight truncate">
              {result.provider_name}
            </h3>

            {/* Rating */}
            <div className="flex items-center gap-1">
              <StarIcon className="size-3.5 fill-amber-400 text-amber-400" />
              <span className="text-sm tabular-nums font-medium">
                {result.rating.toFixed(1)}
              </span>
              <span className="text-xs text-muted-foreground">
                ({result.review_count})
              </span>
            </div>

            {/* Slot */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarIcon className="size-3" />
                {date}
              </span>
              <span className="flex items-center gap-1">
                <ClockIcon className="size-3" />
                {time}
              </span>
              {result.travel_minutes != null && (
                <span className="flex items-center gap-1">
                  <CarIcon className="size-3" />
                  {Math.round(result.travel_minutes)} min
                </span>
              )}
            </div>

            {/* Notes */}
            {result.notes && (
              <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <StickyNoteIcon className="size-3 mt-0.5 shrink-0" />
                <span className="italic">{result.notes}</span>
              </p>
            )}
          </div>

          {/* Right: select button */}
          <div className="shrink-0 pt-1">
            <Button
              size="sm"
              variant={isTop ? "default" : "outline"}
              onClick={() => onSelect?.(result)}
            >
              Select
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

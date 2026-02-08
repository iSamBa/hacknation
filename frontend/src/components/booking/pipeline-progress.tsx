"use client";

import { useState } from "react";
import {
  AlertCircleIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  CircleDotIcon,
  CircleIcon,
  LoaderCircleIcon,
  PhoneCallIcon,
  SearchIcon,
  ListChecksIcon,
  SparklesIcon,
  StarIcon,
  CheckIcon,
  XIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ShortlistItem } from "@/lib/types/booking";

const PIPELINE_PHASES = [
  { key: "searching", label: "Searching", icon: SearchIcon },
  { key: "shortlisting", label: "Shortlisting", icon: ListChecksIcon },
  { key: "calling", label: "Calling", icon: PhoneCallIcon },
  { key: "options_ready", label: "Ready", icon: SparklesIcon },
] as const;

type PhaseKey = (typeof PIPELINE_PHASES)[number]["key"];

export interface PhaseData {
  providerCount: number;
  shortlist: ShortlistItem[];
}

const PHASE_ORDER: Record<string, number> = Object.fromEntries(
  PIPELINE_PHASES.map((p, i) => [p.key, i]),
);

function getPhaseIndex(status: string | null): number {
  if (!status) return -1;
  return PHASE_ORDER[status] ?? -1;
}

type PhaseState = "completed" | "active" | "pending";

function getPhaseState(
  phaseIndex: number,
  currentIndex: number,
  isFailed: boolean,
): PhaseState {
  if (isFailed && phaseIndex === currentIndex) return "active";
  if (phaseIndex < currentIndex) return "completed";
  if (phaseIndex === currentIndex) return "active";
  return "pending";
}

const PREVIEW_COUNT = 3;

interface PipelineProgressProps {
  status: string | null;
  phaseData?: PhaseData;
  className?: string;
}

export function PipelineProgress({
  status,
  phaseData,
  className,
}: PipelineProgressProps) {
  const isFailed = status === "call_failed";
  const currentIndex = getPhaseIndex(isFailed ? "calling" : status);

  return (
    <div className={cn("flex flex-col gap-0", className)}>
      {PIPELINE_PHASES.map((phase, index) => {
        const state = getPhaseState(index, currentIndex, isFailed);
        const isLast = index === PIPELINE_PHASES.length - 1;
        const PhaseIcon = phase.icon;

        return (
          <div key={phase.key} className="flex items-stretch gap-3">
            {/* Vertical line + icon column */}
            <div className="flex flex-col items-center">
              <PhaseIndicator
                state={state}
                isFailed={isFailed && state === "active"}
              />
              {!isLast && (
                <div
                  className={cn(
                    "w-px flex-1 min-h-4",
                    state === "completed" ? "bg-primary" : "bg-border",
                  )}
                />
              )}
            </div>

            {/* Label + inline results */}
            <div className="pb-4 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <PhaseIcon
                  className={cn(
                    "size-4 shrink-0",
                    state === "completed" && "text-primary",
                    state === "active" && !isFailed && "text-primary",
                    state === "active" && isFailed && "text-destructive",
                    state === "pending" && "text-muted-foreground",
                  )}
                />
                <span
                  className={cn(
                    "text-sm font-medium",
                    state === "completed" && "text-primary",
                    state === "active" && !isFailed && "text-foreground",
                    state === "active" && isFailed && "text-destructive",
                    state === "pending" && "text-muted-foreground",
                  )}
                >
                  {phase.label}
                </span>
                {state === "active" && !isFailed && (
                  <LoaderCircleIcon className="text-primary size-3.5 animate-spin" />
                )}
                {state === "active" && isFailed && (
                  <span className="text-destructive text-xs">Failed</span>
                )}
              </div>

              {/* Inline results for completed phases */}
              {state === "completed" && phaseData && (
                <PhaseResults phaseKey={phase.key} data={phaseData} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PhaseResults({
  phaseKey,
  data,
}: {
  phaseKey: PhaseKey;
  data: PhaseData;
}) {
  const [expanded, setExpanded] = useState(false);

  if (phaseKey === "searching") {
    return (
      <p className="mt-0.5 text-xs text-muted-foreground">
        Found {data.providerCount} providers
      </p>
    );
  }

  if (phaseKey === "shortlisting" && data.shortlist.length > 0) {
    const hasMore = data.shortlist.length > PREVIEW_COUNT;
    const visible = expanded ? data.shortlist : data.shortlist.slice(0, PREVIEW_COUNT);
    const remaining = data.shortlist.length - PREVIEW_COUNT;

    return (
      <div className="mt-1.5">
        <table className="w-full text-xs text-muted-foreground">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
              <th className="w-6 pr-1 text-right font-medium">#</th>
              <th className="text-left font-medium">Provider</th>
              <th className="w-14 text-right font-medium">Rating</th>
              <th className="w-12 text-right font-medium">Travel</th>
              <th className="w-10 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((item) => (
              <tr key={item.provider_id}>
                <td className="pr-1 text-right tabular-nums text-foreground/60 py-0.5">
                  {item.rank ?? "-"}
                </td>
                <td className="truncate max-w-0 py-0.5">{item.provider_name}</td>
                <td className="text-right tabular-nums py-0.5">
                  <span className="inline-flex items-center gap-0.5">
                    <StarIcon className="size-2.5 fill-amber-400 text-amber-400" />
                    {item.rating.toFixed(1)}
                  </span>
                </td>
                <td className="text-right tabular-nums py-0.5">
                  {item.travel_minutes != null ? `${Math.round(item.travel_minutes)} min` : "-"}
                </td>
                <td className="text-right tabular-nums text-primary font-medium py-0.5">
                  {item.pre_score.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {hasMore && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronDownIcon
              className={cn(
                "size-3 transition-transform",
                expanded && "rotate-180",
              )}
            />
            {expanded ? "Show less" : `+${remaining} more`}
          </button>
        )}
      </div>
    );
  }

  if (phaseKey === "calling" && data.shortlist.length > 0) {
    const calledCount = data.shortlist.filter((s) => s.was_called).length;
    const notCalledCount = data.shortlist.length - calledCount;
    const hasMore = data.shortlist.length > PREVIEW_COUNT;
    const visible = expanded ? data.shortlist : data.shortlist.slice(0, PREVIEW_COUNT);
    const remaining = data.shortlist.length - PREVIEW_COUNT;

    return (
      <div className="mt-1">
        <p className="text-xs text-muted-foreground">
          <span className="text-green-600 font-medium">{calledCount}</span>
          {" called"}
          {notCalledCount > 0 && (
            <>
              {" / "}
              <span className="font-medium">{notCalledCount}</span>
              {" skipped"}
            </>
          )}
        </p>
        <table className="mt-1 w-full text-xs text-muted-foreground">
          <tbody>
            {visible.map((item) => (
              <tr key={item.provider_id}>
                <td className="w-5 py-0.5">
                  {item.was_called ? (
                    <CheckIcon className="size-3 text-green-600" />
                  ) : (
                    <XIcon className="size-3 text-muted-foreground/40" />
                  )}
                </td>
                <td className="truncate max-w-0 py-0.5">{item.provider_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {hasMore && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronDownIcon
              className={cn(
                "size-3 transition-transform",
                expanded && "rotate-180",
              )}
            />
            {expanded ? "Show less" : `+${remaining} more`}
          </button>
        )}
      </div>
    );
  }

  if (phaseKey === "options_ready" && data.shortlist.length > 0) {
    const calledCount = data.shortlist.filter((s) => s.was_called).length;
    return (
      <p className="mt-0.5 text-xs text-muted-foreground">
        {calledCount} of {data.shortlist.length} providers contacted
      </p>
    );
  }

  return null;
}

function PhaseIndicator({
  state,
  isFailed,
}: {
  state: PhaseState;
  isFailed: boolean;
}) {
  if (state === "completed") {
    return <CheckCircle2Icon className="text-primary size-5 shrink-0" />;
  }
  if (state === "active" && isFailed) {
    return <AlertCircleIcon className="text-destructive size-5 shrink-0" />;
  }
  if (state === "active") {
    return <CircleDotIcon className="text-primary size-5 shrink-0" />;
  }
  return <CircleIcon className="text-muted-foreground size-5 shrink-0" />;
}

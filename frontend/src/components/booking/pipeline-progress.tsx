"use client";

import {
  AlertCircleIcon,
  CheckCircle2Icon,
  CircleDotIcon,
  CircleIcon,
  LoaderCircleIcon,
  PhoneCallIcon,
  SearchIcon,
  ListChecksIcon,
  SparklesIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PIPELINE_PHASES = [
  { key: "searching", label: "Searching", icon: SearchIcon },
  { key: "shortlisting", label: "Shortlisting", icon: ListChecksIcon },
  { key: "calling", label: "Calling", icon: PhoneCallIcon },
  { key: "options_ready", label: "Ready", icon: SparklesIcon },
] as const;

type PhaseKey = (typeof PIPELINE_PHASES)[number]["key"];

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

interface PipelineProgressProps {
  status: string | null;
  className?: string;
}

export function PipelineProgress({ status, className }: PipelineProgressProps) {
  const isFailed = status === "call_failed";
  const currentIndex = getPhaseIndex(isFailed ? "searching" : status);

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
                    "w-px flex-1 min-h-6",
                    state === "completed"
                      ? "bg-primary"
                      : "bg-border",
                  )}
                />
              )}
            </div>

            {/* Label */}
            <div className="flex items-center gap-2 pb-6">
              <PhaseIcon
                className={cn(
                  "size-4",
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
          </div>
        );
      })}
    </div>
  );
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

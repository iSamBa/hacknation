"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  CalendarIcon,
  CheckCircle2Icon,
  ClockIcon,
  MapPinIcon,
  MessageSquareQuoteIcon,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type {
  BookingDetail,
  ConfirmBookingResponse,
  ResultItem,
  ShortlistItem,
} from "@/lib/types/booking";
import { useBookingStatus } from "@/lib/hooks/use-booking-status";
import {
  PipelineProgress,
  type PhaseData,
} from "@/components/booking/pipeline-progress";
import { ConfirmationDialog } from "@/components/booking/confirmation-dialog";
import { ConversationPlayer } from "@/components/booking/conversation-player";
import { ResultsList } from "@/components/booking/results-list";
import { StatusBadge } from "@/components/booking/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const TERMINAL_STATUSES = new Set(["options_ready", "confirmed", "cancelled"]);
const HAS_SHORTLIST_DATA = new Set([
  "shortlisting", "calling", "collecting", "ranking",
  "options_ready", "confirmed",
]);

interface BookingDetailViewProps {
  bookingId: string;
}

export function BookingDetailView({ bookingId }: BookingDetailViewProps) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [shortlist, setShortlist] = useState<ShortlistItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ResultItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmation, setConfirmation] =
    useState<ConfirmBookingResponse | null>(null);
  const { status: liveStatus, providerCount } = useBookingStatus(bookingId);

  const displayStatus = confirmation
    ? "confirmed"
    : (liveStatus ?? booking?.status ?? null);

  const fetchBooking = useCallback(() => {
    apiGet<BookingDetail>(`/api/bookings/${bookingId}`)
      .then(setBooking)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load booking"),
      );
  }, [bookingId]);

  const fetchShortlist = useCallback(() => {
    apiGet<ShortlistItem[]>(`/api/bookings/${bookingId}/shortlist`)
      .then(setShortlist)
      .catch(() => {
        // Shortlist may not exist yet
      });
  }, [bookingId]);

  useEffect(() => {
    fetchBooking();
    fetchShortlist();
  }, [fetchBooking, fetchShortlist]);

  // Re-fetch booking and shortlist as pipeline status advances (via WS or polling)
  const lastFetchedStatus = useRef<string | null>(null);

  useEffect(() => {
    if (!liveStatus || liveStatus === lastFetchedStatus.current) return;
    lastFetchedStatus.current = liveStatus;

    if (HAS_SHORTLIST_DATA.has(liveStatus)) {
      fetchShortlist();
    }
    fetchBooking();
  }, [liveStatus, fetchShortlist, fetchBooking]);

  const phaseData = useMemo<PhaseData | undefined>(() => {
    if (shortlist.length === 0 && !providerCount) return undefined;
    return {
      providerCount: providerCount ?? shortlist.length,
      shortlist,
    };
  }, [shortlist, providerCount]);

  if (error) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <BackLink />
        <h1 className="text-2xl font-semibold">Booking Not Found</h1>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <div className="bg-muted h-4 w-20 animate-pulse rounded" />
        <div className="bg-muted h-7 w-48 animate-pulse rounded" />
        <div className="bg-muted h-64 animate-pulse rounded-xl" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      {/* Back + Header */}
      <div>
        <BackLink />
        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-semibold capitalize tracking-tight">
            {booking.service_type}
          </h1>
          {displayStatus && <StatusBadge status={displayStatus} />}
        </div>
        {/* Inline metadata */}
        <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {booking.preferred_date && (
            <span className="flex items-center gap-1">
              <CalendarIcon className="size-3" />
              {booking.preferred_date}
            </span>
          )}
          {booking.preferred_time && (
            <span className="flex items-center gap-1">
              <ClockIcon className="size-3" />
              <span className="capitalize">{booking.preferred_time}</span>
            </span>
          )}
          {booking.location_override && (
            <span className="flex items-center gap-1">
              <MapPinIcon className="size-3" />
              {booking.location_override}
            </span>
          )}
        </div>
      </div>

      {/* Pipeline Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <PipelineProgress status={displayStatus} phaseData={phaseData} />
        </CardContent>
      </Card>

      {/* Active Conversation Player */}
      {displayStatus === "calling" && (
        <ConversationPlayer bookingId={bookingId} />
      )}

      {/* Confirmed Summary */}
      {confirmation && (
        <Card className="border-green-200 dark:border-green-800">
          <CardContent className="pt-5">
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <CheckCircle2Icon className="size-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-semibold">
                  {confirmation.provider_name}
                </p>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <MapPinIcon className="size-3 shrink-0" />
                  {confirmation.provider_address}
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="size-3" />
                    {new Date(confirmation.slot).toLocaleDateString("en-US", {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <span className="flex items-center gap-1">
                    <ClockIcon className="size-3" />
                    {new Date(confirmation.slot).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                      hour12: true,
                    })}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results List (only when options_ready and not yet confirmed) */}
      {displayStatus === "options_ready" && !confirmation && (
        <ResultsList
          bookingId={bookingId}
          onSelect={(result) => {
            setSelectedResult(result);
            setDialogOpen(true);
          }}
        />
      )}

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        bookingId={bookingId}
        result={selectedResult}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onConfirmed={(response) => {
          setConfirmation(response);
          setDialogOpen(false);
        }}
      />

      {/* Original request */}
      <Card>
        <CardContent className="pt-5">
          <div className="flex items-start gap-2.5">
            <MessageSquareQuoteIcon className="text-muted-foreground size-4 mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              &quot;{booking.raw_message}&quot;
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/bookings"
      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
    >
      <ArrowLeftIcon className="size-3" />
      Bookings
    </Link>
  );
}

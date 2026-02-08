"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  MessageSquareQuoteIcon,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { BookingDetail, ShortlistItem } from "@/lib/types/booking";
import { useBookingStatus } from "@/lib/hooks/use-booking-status";
import {
  PipelineProgress,
  type PhaseData,
} from "@/components/booking/pipeline-progress";
import { StatusBadge } from "@/components/booking/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const TERMINAL_STATUSES = new Set(["options_ready", "confirmed", "cancelled"]);

interface BookingDetailViewProps {
  bookingId: string;
}

export function BookingDetailView({ bookingId }: BookingDetailViewProps) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [shortlist, setShortlist] = useState<ShortlistItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { status: wsStatus, providerCount } = useBookingStatus(bookingId);
  const hasRefetchedRef = useRef(false);

  const displayStatus = wsStatus ?? booking?.status ?? null;

  const fetchShortlist = useCallback(() => {
    apiGet<ShortlistItem[]>(`/api/bookings/${bookingId}/shortlist`)
      .then(setShortlist)
      .catch(() => {
        // Shortlist may not exist yet
      });
  }, [bookingId]);

  useEffect(() => {
    apiGet<BookingDetail>(`/api/bookings/${bookingId}`)
      .then(setBooking)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load booking"),
      );
    fetchShortlist();
  }, [bookingId, fetchShortlist]);

  // Re-fetch shortlist when pipeline reaches a terminal state
  useEffect(() => {
    if (wsStatus && TERMINAL_STATUSES.has(wsStatus) && !hasRefetchedRef.current) {
      hasRefetchedRef.current = true;
      fetchShortlist();
    }
  }, [wsStatus, fetchShortlist]);

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

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CalendarIcon,
  ChevronRightIcon,
  PhoneCallIcon,
  UsersIcon,
  LoaderCircleIcon,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { BookingListItem } from "@/lib/types/booking";
import { StatusBadge } from "@/components/booking/status-badge";

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function BookingStatusLine({ booking }: { booking: BookingListItem }) {
  const parts: React.ReactNode[] = [];

  if (booking.preferred_date) {
    parts.push(
      <span key="date" className="flex items-center gap-1">
        <CalendarIcon className="size-3 shrink-0" />
        {booking.preferred_date}
      </span>,
    );
  }

  if (booking.provider_count > 0) {
    parts.push(
      <span key="providers" className="flex items-center gap-1">
        <UsersIcon className="size-3 shrink-0" />
        {booking.provider_count}
      </span>,
    );
  }

  if (booking.called_count > 0) {
    parts.push(
      <span key="called" className="flex items-center gap-1">
        <PhoneCallIcon className="size-3 shrink-0" />
        {booking.called_count} called
      </span>,
    );
  }

  const isProcessing = ["searching", "shortlisting", "calling"].includes(
    booking.status,
  );
  if (parts.length === 0 && isProcessing) {
    parts.push(
      <span key="processing" className="flex items-center gap-1">
        <LoaderCircleIcon className="size-3 shrink-0 animate-spin" />
        Processing...
      </span>,
    );
  }

  if (parts.length === 0) {
    parts.push(
      <span key="created">
        Created {formatDate(booking.created_at)}
      </span>,
    );
  }

  return (
    <div className="flex items-center gap-3 text-xs text-muted-foreground">
      {parts}
    </div>
  );
}

export default function BookingsPage() {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<BookingListItem[]>("/api/bookings")
      .then(setBookings)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Failed to load bookings",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight">My Bookings</h1>

      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

      {loading && (
        <div className="mt-4 divide-y rounded-lg border">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <div className="flex-1 space-y-2">
                <div className="bg-muted h-4 w-28 animate-pulse rounded" />
                <div className="bg-muted h-3 w-40 animate-pulse rounded" />
              </div>
              <div className="bg-muted h-5 w-16 animate-pulse rounded-full" />
            </div>
          ))}
        </div>
      )}

      {!loading && !error && bookings.length === 0 && (
        <div className="mt-8 text-center">
          <p className="text-muted-foreground">
            No bookings yet. Start a conversation to create one.
          </p>
        </div>
      )}

      {!loading && bookings.length > 0 && (
        <div className="mt-4 divide-y rounded-lg border">
          {bookings.map((booking) => (
            <Link
              key={booking.id}
              href={`/bookings/${booking.id}`}
              className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/50"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium capitalize leading-tight truncate">
                  {booking.service_type}
                </p>
                <BookingStatusLine booking={booking} />
              </div>
              <StatusBadge status={booking.status} />
              <ChevronRightIcon className="size-4 text-muted-foreground shrink-0 opacity-0 -translate-x-1 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

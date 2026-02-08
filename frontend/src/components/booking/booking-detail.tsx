"use client";

import { useEffect, useState } from "react";
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  TagIcon,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import { useBookingStatus } from "@/lib/hooks/use-booking-status";
import { PipelineProgress } from "@/components/booking/pipeline-progress";
import { StatusBadge } from "@/components/booking/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export interface BookingDetail {
  id: string;
  status: string;
  service_type: string;
  preferred_date: string | null;
  preferred_time: string | null;
  location_override: string | null;
  raw_message: string;
  created_at: string;
}

interface BookingDetailViewProps {
  bookingId: string;
}

export function BookingDetailView({ bookingId }: BookingDetailViewProps) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { status: wsStatus } = useBookingStatus(bookingId);

  const displayStatus = wsStatus ?? booking?.status ?? null;

  useEffect(() => {
    apiGet<BookingDetail>(`/api/bookings/${bookingId}`)
      .then(setBooking)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load booking"),
      );
  }, [bookingId]);

  if (error) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <h1 className="text-2xl font-semibold">Booking Not Found</h1>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <div className="bg-muted h-8 w-48 animate-pulse rounded" />
        <div className="bg-muted h-48 animate-pulse rounded-xl" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold capitalize">
          {booking.service_type}
        </h1>
        {displayStatus && <StatusBadge status={displayStatus} />}
      </div>

      {/* Pipeline Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Pipeline Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <PipelineProgress status={displayStatus} />
        </CardContent>
      </Card>

      {/* Booking Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Request Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <div className="flex items-center gap-2">
            <TagIcon className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">Service:</span>
            <span className="font-medium capitalize">
              {booking.service_type}
            </span>
          </div>

          {booking.preferred_date && (
            <div className="flex items-center gap-2">
              <CalendarIcon className="text-muted-foreground size-3.5" />
              <span className="text-muted-foreground">Date:</span>
              <span className="font-medium">{booking.preferred_date}</span>
            </div>
          )}

          {booking.preferred_time && (
            <div className="flex items-center gap-2">
              <ClockIcon className="text-muted-foreground size-3.5" />
              <span className="text-muted-foreground">Time:</span>
              <span className="font-medium capitalize">
                {booking.preferred_time}
              </span>
            </div>
          )}

          {booking.location_override && (
            <div className="flex items-center gap-2">
              <MapPinIcon className="text-muted-foreground size-3.5" />
              <span className="text-muted-foreground">Location:</span>
              <span className="font-medium">{booking.location_override}</span>
            </div>
          )}

          <div className="border-t pt-3">
            <p className="text-muted-foreground italic">
              &quot;{booking.raw_message}&quot;
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

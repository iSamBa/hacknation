"use client";

import { useState } from "react";
import {
  CalendarIcon,
  CheckCircle2Icon,
  ClockIcon,
  LoaderCircleIcon,
  MapPinIcon,
  StarIcon,
} from "lucide-react";
import { apiPost } from "@/lib/api";
import type {
  ConfirmBookingResponse,
  ResultItem,
} from "@/lib/types/booking";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ConfirmationDialogProps {
  bookingId: string;
  result: ResultItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirmed: (response: ConfirmBookingResponse) => void;
}

function formatSlot(slot: string): { date: string; time: string } {
  const d = new Date(slot);
  const date = d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return { date, time };
}

export function ConfirmationDialog({
  bookingId,
  result,
  open,
  onOpenChange,
  onConfirmed,
}: ConfirmationDialogProps) {
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState<ConfirmBookingResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  if (!result) return null;

  const { date, time } = formatSlot(result.slot);

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      const response = await apiPost<ConfirmBookingResponse>(
        `/api/bookings/${bookingId}/confirm`,
        {
          provider_id: result.provider_id,
          slot: result.slot,
        },
      );
      setConfirmed(response);
      onConfirmed(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to confirm booking",
      );
    } finally {
      setConfirming(false);
    }
  };

  const handleClose = () => {
    if (!confirming) {
      setConfirmed(null);
      setError(null);
      onOpenChange(false);
    }
  };

  // Success state
  if (confirmed) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent>
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="flex size-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle2Icon className="size-8 text-green-600 dark:text-green-400" />
            </div>
            <DialogHeader className="items-center">
              <DialogTitle>Booking Confirmed!</DialogTitle>
              <DialogDescription>
                Your appointment has been booked successfully.
              </DialogDescription>
            </DialogHeader>
            <div className="w-full rounded-lg border p-4 space-y-2">
              <p className="font-semibold text-sm">
                {confirmed.provider_name}
              </p>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPinIcon className="size-3 shrink-0" />
                {confirmed.provider_address}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <CalendarIcon className="size-3" />
                  {formatSlot(confirmed.slot).date}
                </span>
                <span className="flex items-center gap-1">
                  <ClockIcon className="size-3" />
                  {formatSlot(confirmed.slot).time}
                </span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleClose} className="w-full sm:w-auto">
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  // Confirmation state
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Booking</DialogTitle>
          <DialogDescription>
            Review the details below and confirm your appointment.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Provider details */}
          <div className="rounded-lg border p-4 space-y-2.5">
            <h3 className="font-semibold text-sm">{result.provider_name}</h3>
            <div className="flex items-center gap-1">
              <StarIcon className="size-3.5 fill-amber-400 text-amber-400" />
              <span className="text-sm tabular-nums font-medium">
                {result.rating.toFixed(1)}
              </span>
              <span className="text-xs text-muted-foreground">
                ({result.review_count} reviews)
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarIcon className="size-3" />
                {date}
              </span>
              <span className="flex items-center gap-1">
                <ClockIcon className="size-3" />
                {time}
              </span>
            </div>
            {result.notes && (
              <p className="text-xs text-muted-foreground italic">
                {result.notes}
              </p>
            )}
          </div>

          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={confirming}
          >
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={confirming}>
            {confirming && (
              <LoaderCircleIcon className="mr-2 size-4 animate-spin" />
            )}
            Confirm Booking
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

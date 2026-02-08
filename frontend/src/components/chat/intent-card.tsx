"use client";

import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  SearchIcon,
  SparklesIcon,
  TagIcon,
  ZapIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { BookingIntent } from "@/lib/hooks/use-chat";

interface IntentCardProps {
  intent: BookingIntent;
  bookingId?: string;
  onFindProviders?: (bookingId: string) => void;
}

const urgencyLabels: Record<string, { label: string; variant: "default" | "secondary" | "destructive" }> = {
  asap: { label: "ASAP", variant: "destructive" },
  flexible: { label: "Flexible", variant: "secondary" },
  specific_date: { label: "Specific Date", variant: "default" },
};

export function IntentCard({
  intent,
  bookingId,
  onFindProviders,
}: IntentCardProps) {
  const urgency = urgencyLabels[intent.urgency] ?? urgencyLabels.flexible;

  return (
    <Card className="w-full gap-3 py-3">
      <CardHeader className="gap-1 px-4 pb-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <SparklesIcon className="text-primary size-4" />
            Parsed Request
          </CardTitle>
          <Badge variant={urgency.variant}>{urgency.label}</Badge>
        </div>
      </CardHeader>

      <CardContent className="grid gap-2 px-4 text-sm">
        <div className="flex items-center gap-2">
          <TagIcon className="text-muted-foreground size-3.5" />
          <span className="text-muted-foreground">Service:</span>
          <span className="font-medium">{intent.service_type}</span>
        </div>

        {intent.date && (
          <div className="flex items-center gap-2">
            <CalendarIcon className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">Date:</span>
            <span className="font-medium">{intent.date}</span>
          </div>
        )}

        {intent.time_preference && (
          <div className="flex items-center gap-2">
            <ClockIcon className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">Time:</span>
            <span className="font-medium capitalize">
              {intent.time_preference}
            </span>
          </div>
        )}

        {intent.location_override && (
          <div className="flex items-center gap-2">
            <MapPinIcon className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">Location:</span>
            <span className="font-medium">{intent.location_override}</span>
          </div>
        )}

        {intent.constraints.length > 0 && (
          <div className="flex items-start gap-2">
            <ZapIcon className="text-muted-foreground mt-0.5 size-3.5" />
            <span className="text-muted-foreground">Requirements:</span>
            <div className="flex flex-wrap gap-1">
              {intent.constraints.map((constraint) => (
                <Badge key={constraint} variant="outline" className="text-xs">
                  {constraint}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      {bookingId && onFindProviders && (
        <CardFooter className="px-4 pt-0">
          <Button
            onClick={() => onFindProviders(bookingId)}
            className="w-full"
            size="sm"
          >
            <SearchIcon className="size-4" />
            Find Providers
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}

"use client";

import { Phone } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/lib/api";
import type { BookingDetail } from "@/lib/types/booking";

interface ConversationPlayerProps {
  bookingId: string;
}

// Declare the custom element for TypeScript
declare global {
  namespace JSX {
    interface IntrinsicElements {
      "elevenlabs-convai": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          "agent-id"?: string;
          "dynamic-variables"?: string;
        },
        HTMLElement
      >;
    }
  }
}

interface UserProfile {
  id: string;
  name: string;
  phone: string | null;
}

interface ShortlistItem {
  provider_id: string;
  provider_name: string;
  rank: number;
}

export function ConversationPlayer({ bookingId }: ConversationPlayerProps) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [dynamicVariables, setDynamicVariables] = useState<string>("");

  // Fetch booking, user profile, and shortlist data
  useEffect(() => {
    async function fetchData() {
      try {
        const [bookingData, profileData, shortlistData] = await Promise.all([
          apiGet<BookingDetail>(`/api/bookings/${bookingId}`),
          apiGet<UserProfile>("/api/users/me"),
          apiGet<ShortlistItem[]>(`/api/bookings/${bookingId}/shortlist`),
        ]);
        setBooking(bookingData);
        setUserProfile(profileData);

        // Get the top-ranked provider (rank = 1)
        const topProvider = shortlistData.find((item) => item.rank === 1);
        const providerName = topProvider?.provider_name || "Demo Provider";

        // Build dynamic variables JSON string
        const vars = {
          patient_name: profileData.name,
          service_type: bookingData.service_type,
          preferred_date: bookingData.preferred_date || "flexible",
          preferred_time: bookingData.preferred_time || "flexible",
          patient_phone: profileData.phone || "not provided",
          provider_name: providerName,
        };

        setDynamicVariables(JSON.stringify(vars));
        console.log("Widget variables:", vars);
      } catch (error) {
        console.error("Failed to fetch booking data:", error);
      }
    }
    fetchData();
  }, [bookingId]);

  if (!booking || !userProfile) {
    return (
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Loading conversation...
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg text-blue-900 dark:text-blue-100">
          <Phone className="h-5 w-5 animate-pulse" />
          Talk to the AI Agent
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* ElevenLabs Widget */}
        <div className="flex items-center justify-center py-8">
          <elevenlabs-convai
            agent-id="agent_6101kgx7fznhfq3bpdzrja5aer3t"
            dynamic-variables={dynamicVariables}
          />
        </div>
      </CardContent>
    </Card>
  );
}

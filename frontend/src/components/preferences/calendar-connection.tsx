"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Calendar, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface GoogleAuthStatus {
  connected: boolean;
  scopes: string[];
}

export function CalendarConnection() {
  const [status, setStatus] = useState<GoogleAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/auth/google/status`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch calendar status");
      }
      const data: GoogleAuthStatus = await response.json();
      setStatus(data);
    } catch (error) {
      console.error("Failed to fetch calendar status:", error);
      toast.error("Failed to load calendar connection status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    // Check for success query param (redirect from OAuth callback)
    const params = new URLSearchParams(window.location.search);
    if (params.get("calendar") === "connected") {
      toast.success("Google Calendar connected successfully");
      // Clean up URL
      window.history.replaceState({}, "", window.location.pathname);
      // Refresh status
      fetchStatus();
    }
  }, [fetchStatus]);

  const handleConnect = useCallback(async () => {
    setActionLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/auth/google/authorize`
      );
      if (!response.ok) {
        throw new Error("Failed to start authorization");
      }
      const data: { authorization_url: string; state: string } =
        await response.json();

      // Redirect to Google consent screen
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error("Failed to connect calendar:", error);
      toast.error("Failed to start Google Calendar connection");
      setActionLoading(false);
    }
  }, []);

  const handleDisconnect = useCallback(async () => {
    setActionLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/auth/google/disconnect`,
        {
          method: "POST",
        }
      );
      if (!response.ok) {
        throw new Error("Failed to disconnect");
      }
      toast.success("Google Calendar disconnected");
      await fetchStatus();
    } catch (error) {
      console.error("Failed to disconnect calendar:", error);
      toast.error("Failed to disconnect Google Calendar");
    } finally {
      setActionLoading(false);
    }
  }, [fetchStatus]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Google Calendar</CardTitle>
          <CardDescription>
            Connect your calendar to check real availability.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-6">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="size-5" />
          Google Calendar
        </CardTitle>
        <CardDescription>
          Connect your calendar to automatically check your availability before
          booking appointments.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status?.connected ? (
          <>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-5 text-green-600" />
              <span className="font-medium">Connected</span>
            </div>

            {status.scopes.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Permissions:</p>
                <div className="flex flex-wrap gap-2">
                  {status.scopes.map((scope) => (
                    <Badge key={scope} variant="secondary">
                      {scope.split("/").pop()?.replace("calendar.", "")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <Button
              variant="outline"
              onClick={handleDisconnect}
              disabled={actionLoading}
            >
              {actionLoading && <Loader2 className="animate-spin" />}
              Disconnect
            </Button>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2 text-muted-foreground">
              <XCircle className="size-5" />
              <span>Not connected</span>
            </div>

            <Button onClick={handleConnect} disabled={actionLoading}>
              {actionLoading && <Loader2 className="animate-spin" />}
              Connect Google Calendar
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { InboxIcon, LoaderCircleIcon } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { ResultItem } from "@/lib/types/booking";
import { ProviderCard } from "@/components/booking/provider-card";

interface ResultsListProps {
  bookingId: string;
  onSelect?: (result: ResultItem) => void;
}

export function ResultsList({ bookingId, onSelect }: ResultsListProps) {
  const [results, setResults] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResults = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<ResultItem[]>(
        `/api/bookings/${bookingId}/results`,
      );
      setResults(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load results",
      );
    } finally {
      setLoading(false);
    }
  }, [bookingId]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8" role="status">
        <LoaderCircleIcon className="text-muted-foreground size-5 animate-spin" aria-hidden="true" />
        <span className="ml-2 text-sm text-muted-foreground">
          Loading results...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <p className="py-4 text-center text-sm text-destructive">{error}</p>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
        <InboxIcon className="size-8" />
        <p className="text-sm">No providers found available slots.</p>
        <p className="text-xs">Try adjusting your preferences or date.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">
          Available Options
        </h2>
        <span className="text-xs text-muted-foreground">
          {results.length} result{results.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="space-y-3">
        {results.map((result) => (
          <ProviderCard
            key={result.provider_id}
            result={result}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

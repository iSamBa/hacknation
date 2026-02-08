"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPut } from "@/lib/api";

export interface UserProfile {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  address: string;
  latitude: number;
  longitude: number;
  preferred_times: string[];
  preferred_days: string[];
  avoid_times: string[] | null;
  max_distance_km: number;
  min_rating: number;
  shortlist_count: number;
  preferred_providers: string[];
  blocked_providers: string[];
  language_preference: string;
  transport_mode: string;
  google_calendar_id: string | null;
  created_at: string;
  updated_at: string;
}

export type UserProfileUpdate = Partial<
  Omit<UserProfile, "id" | "created_at" | "updated_at">
>;

export function useUserProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<UserProfile>("/api/users/me");
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, []);

  const updateProfile = useCallback(
    async (data: UserProfileUpdate) => {
      const updated = await apiPut<UserProfile>("/api/users/me", data);
      setProfile(updated);
      return updated;
    },
    [],
  );

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  return { profile, loading, error, updateProfile, refetch: fetchProfile };
}

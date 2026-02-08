"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { TimePreferences } from "@/components/preferences/time-preferences";
import { DaySelector } from "@/components/preferences/day-selector";
import { DistanceSlider } from "@/components/preferences/distance-slider";
import { RatingSlider } from "@/components/preferences/rating-slider";
import { AddressAutocomplete } from "@/components/preferences/address-autocomplete";
import {
  useUserProfile,
  type UserProfileUpdate,
} from "@/lib/hooks/use-user-profile";

const LANGUAGES = [
  { value: "english", label: "English" },
  { value: "french", label: "French" },
  { value: "german", label: "German" },
  { value: "spanish", label: "Spanish" },
  { value: "italian", label: "Italian" },
  { value: "portuguese", label: "Portuguese" },
  { value: "dutch", label: "Dutch" },
  { value: "arabic", label: "Arabic" },
];

export default function PreferencesPage() {
  const { profile, loading, error, updateProfile } = useUserProfile();
  const [saving, setSaving] = useState(false);

  const [address, setAddress] = useState("");
  const [latitude, setLatitude] = useState(0);
  const [longitude, setLongitude] = useState(0);
  const [preferredTimes, setPreferredTimes] = useState<string[]>([]);
  const [preferredDays, setPreferredDays] = useState<string[]>([]);
  const [maxDistance, setMaxDistance] = useState(10);
  const [minRating, setMinRating] = useState(4.0);
  const [language, setLanguage] = useState("english");

  const profileIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (profile && profile.id !== profileIdRef.current) {
      profileIdRef.current = profile.id;
      setAddress(profile.address);
      setLatitude(profile.latitude);
      setLongitude(profile.longitude);
      setPreferredTimes(profile.preferred_times);
      setPreferredDays(profile.preferred_days);
      setMaxDistance(profile.max_distance_km);
      setMinRating(profile.min_rating);
      setLanguage(profile.language_preference);
    }
  }, [profile]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const data: UserProfileUpdate = {
        address,
        latitude,
        longitude,
        preferred_times: preferredTimes,
        preferred_days: preferredDays,
        max_distance_km: maxDistance,
        min_rating: minRating,
        language_preference: language,
      };
      await updateProfile(data);
      toast.success("Preferences saved successfully");
    } catch {
      toast.error("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  }, [
    address,
    latitude,
    longitude,
    preferredTimes,
    preferredDays,
    maxDistance,
    minRating,
    language,
    updateProfile,
  ]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-20 text-center">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Preferences</h1>
        <p className="mt-1 text-muted-foreground">
          Configure your booking preferences and settings.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Location</CardTitle>
          <CardDescription>
            Set your address for finding nearby providers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="address">Address</Label>
            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onAddressSelect={(data) => {
                setLatitude(data.latitude);
                setLongitude(data.longitude);
              }}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scheduling</CardTitle>
          <CardDescription>
            Choose when you prefer appointments.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <TimePreferences
            value={preferredTimes}
            onChange={setPreferredTimes}
          />
          <Separator />
          <DaySelector value={preferredDays} onChange={setPreferredDays} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Provider Preferences</CardTitle>
          <CardDescription>
            Set your distance and quality thresholds.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <DistanceSlider value={maxDistance} onChange={setMaxDistance} />
          <Separator />
          <RatingSlider value={minRating} onChange={setMinRating} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Language</CardTitle>
          <CardDescription>
            Preferred language for provider communication.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label>Language</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((lang) => (
                  <SelectItem key={lang.value} value={lang.value}>
                    {lang.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end pb-6">
        <Button onClick={handleSave} disabled={saving}>
          {saving && <Loader2 className="animate-spin" />}
          {saving ? "Saving..." : "Save Preferences"}
        </Button>
      </div>
    </div>
  );
}

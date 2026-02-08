"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

const TIME_SLOTS = [
  { value: "morning", label: "Morning", description: "8am - 12pm" },
  { value: "afternoon", label: "Afternoon", description: "12pm - 5pm" },
  { value: "evening", label: "Evening", description: "5pm - 8pm" },
];

interface TimePreferencesProps {
  value: string[];
  onChange: (value: string[]) => void;
}

export function TimePreferences({ value, onChange }: TimePreferencesProps) {
  function toggle(slot: string) {
    if (value.includes(slot)) {
      onChange(value.filter((v) => v !== slot));
    } else {
      onChange([...value, slot]);
    }
  }

  return (
    <div className="space-y-3">
      <Label className="text-base font-semibold">Preferred Times</Label>
      <div className="grid gap-3 sm:grid-cols-3">
        {TIME_SLOTS.map((slot) => (
          <label
            key={slot.value}
            className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent"
          >
            <Checkbox
              checked={value.includes(slot.value)}
              onCheckedChange={() => toggle(slot.value)}
            />
            <div>
              <div className="text-sm font-medium">{slot.label}</div>
              <div className="text-xs text-muted-foreground">
                {slot.description}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}

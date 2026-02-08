"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface DaySelectorProps {
  value: string[];
  onChange: (value: string[]) => void;
}

export function DaySelector({ value, onChange }: DaySelectorProps) {
  function toggle(day: string) {
    if (value.includes(day)) {
      onChange(value.filter((v) => v !== day));
    } else {
      onChange([...value, day]);
    }
  }

  return (
    <div className="space-y-3">
      <Label className="text-base font-semibold">Preferred Days</Label>
      <div className="flex flex-wrap gap-2">
        {DAYS.map((day) => (
          <Button
            key={day}
            type="button"
            variant={value.includes(day) ? "default" : "outline"}
            size="sm"
            onClick={() => toggle(day)}
          >
            {day}
          </Button>
        ))}
      </div>
    </div>
  );
}

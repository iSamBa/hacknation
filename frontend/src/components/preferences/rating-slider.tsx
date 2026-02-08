"use client";

import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

interface RatingSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export function RatingSlider({ value, onChange }: RatingSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-base font-semibold">Minimum Rating</Label>
        <span className="text-sm font-medium text-muted-foreground">
          {value.toFixed(1)} / 5.0
        </span>
      </div>
      <Slider
        min={1}
        max={5}
        step={0.5}
        value={[value]}
        onValueChange={(values) => onChange(values[0])}
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>1.0</span>
        <span>5.0</span>
      </div>
    </div>
  );
}

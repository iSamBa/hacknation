"use client";

import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

interface DistanceSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export function DistanceSlider({ value, onChange }: DistanceSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-base font-semibold">Max Distance</Label>
        <span className="text-sm font-medium text-muted-foreground">
          {value} km
        </span>
      </div>
      <Slider
        min={1}
        max={50}
        step={1}
        value={[value]}
        onValueChange={(values) => onChange(values[0])}
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>1 km</span>
        <span>50 km</span>
      </div>
    </div>
  );
}

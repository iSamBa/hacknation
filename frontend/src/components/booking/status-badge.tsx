import { Badge } from "@/components/ui/badge";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: BadgeVariant }
> = {
  searching: { label: "Searching", variant: "secondary" },
  shortlisting: { label: "Shortlisting", variant: "secondary" },
  calling: { label: "Calling", variant: "secondary" },
  collecting: { label: "Collecting", variant: "secondary" },
  ranking: { label: "Ranking", variant: "secondary" },
  options_ready: { label: "Options Ready", variant: "default" },
  confirmed: { label: "Confirmed", variant: "default" },
  cancelled: { label: "Cancelled", variant: "outline" },
  call_failed: { label: "Failed", variant: "destructive" },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    variant: "outline" as BadgeVariant,
  };

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}

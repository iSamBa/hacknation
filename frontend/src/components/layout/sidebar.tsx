"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  List,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

const navItems = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/bookings", label: "My Bookings", icon: List },
  { href: "/preferences", label: "Preferences", icon: Settings },
];

function NavLinks({ onClick }: { onClick?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {navItems.map((item) => {
        const isActive =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);

        return (
          <Button
            key={item.href}
            variant={isActive ? "secondary" : "ghost"}
            size="sm"
            className={cn(
              "justify-start gap-3",
              isActive && "font-semibold"
            )}
            asChild
          >
            <Link href={item.href} onClick={onClick}>
              <item.icon className="size-4" />
              {item.label}
            </Link>
          </Button>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-sidebar md:block">
      <div className="flex h-14 items-center border-b px-4">
        <Link href="/" className="font-semibold text-sidebar-foreground">
          iConcierge
        </Link>
      </div>
      <div className="p-4">
        <NavLinks />
      </div>
    </aside>
  );
}

export function MobileSidebar({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="border-b">
          <SheetTitle>iConcierge</SheetTitle>
        </SheetHeader>
        <div className="p-4">
          <NavLinks onClick={() => onOpenChange(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}

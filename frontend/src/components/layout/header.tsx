"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MobileSidebar } from "@/components/layout/sidebar";

export function Header() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <>
      <header className="flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu className="size-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>
        <span className="font-semibold">iConcierge</span>
      </header>
      <MobileSidebar open={sidebarOpen} onOpenChange={setSidebarOpen} />
    </>
  );
}

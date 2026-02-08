"use client";

import { ChatContainer } from "@/components/chat/chat-container";

export default function DashboardPage() {
  return (
    <div className="-m-6 h-[calc(100vh-3.5rem)] md:h-screen">
      <ChatContainer />
    </div>
  );
}

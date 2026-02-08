"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { BotIcon, Loader2Icon } from "lucide-react";
import {
  AIInput,
  AIInputSubmit,
  AIInputTextarea,
} from "@/components/kibo-ui/ai-input";
import { useChat } from "@/lib/hooks/use-chat";
import { MessageBubble } from "./message-bubble";

export function ChatContainer() {
  const { messages, isLoading, sendMessage } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleFindProviders = (bookingId: string) => {
    router.push(`/bookings/${bookingId}`);
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} role="log" aria-label="Chat messages" className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="bg-muted flex size-16 items-center justify-center rounded-full">
              <BotIcon className="text-muted-foreground size-8" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">
                What can I help you book?
              </h2>
              <p className="text-muted-foreground mt-1 text-sm">
                Describe your booking request in natural language. For example:
              </p>
              <div className="text-muted-foreground mt-3 space-y-1 text-sm italic">
                <p>&ldquo;I need a dentist next Tuesday afternoon&rdquo;</p>
                <p>&ldquo;Find me a plumber ASAP near downtown&rdquo;</p>
                <p>
                  &ldquo;Book a hairdresser for Saturday morning, must accept
                  walk-ins&rdquo;
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-4">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onFindProviders={handleFindProviders}
              />
            ))}

            {isLoading && (
              <div role="status" aria-label="Processing request" className="flex items-center gap-3">
                <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-full">
                  <BotIcon className="size-4" />
                </div>
                <div className="bg-muted flex items-center gap-2 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm">
                  <Loader2Icon className="size-4 animate-spin" />
                  <span className="text-muted-foreground">
                    Thinking...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="border-t p-4">
        <div className="mx-auto max-w-2xl">
          <AIInput onSubmit={sendMessage} disabled={isLoading}>
            <AIInputTextarea />
            <AIInputSubmit loading={isLoading} />
          </AIInput>
        </div>
      </div>
    </div>
  );
}

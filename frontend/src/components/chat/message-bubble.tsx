"use client";

import { AlertCircleIcon, BotIcon, UserIcon } from "lucide-react";
import type { ChatMessage } from "@/lib/hooks/use-chat";
import { IntentCard } from "./intent-card";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
  onFindProviders?: (bookingId: string) => void;
}

export function MessageBubble({ message, onFindProviders }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground",
        )}
      >
        {isUser ? <UserIcon className="size-4" /> : <BotIcon className="size-4" />}
      </div>

      <div
        className={cn(
          "flex max-w-[80%] flex-col gap-2",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : message.error
                ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-bl-md"
                : "bg-muted text-foreground rounded-bl-md",
          )}
        >
          {message.error && (
            <AlertCircleIcon className="mb-1 inline-block size-4 mr-1.5 align-text-bottom" />
          )}
          {message.content}
        </div>

        {message.intent && (
          <IntentCard
            intent={message.intent}
            bookingId={message.bookingId}
            onFindProviders={onFindProviders}
          />
        )}

        <span className="text-muted-foreground px-1 text-xs">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}

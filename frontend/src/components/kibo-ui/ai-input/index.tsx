"use client";

import {
  type FormEvent,
  type HTMLAttributes,
  type KeyboardEvent,
  type TextareaHTMLAttributes,
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import { SendIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type AIInputContextProps = {
  value: string;
  setValue: (value: string) => void;
  disabled: boolean;
};

const AIInputContext = createContext<AIInputContextProps>({
  value: "",
  setValue: () => {},
  disabled: false,
});

export type AIInputProps = Omit<HTMLAttributes<HTMLFormElement>, "onSubmit"> & {
  onSubmit: (value: string) => void;
  disabled?: boolean;
};

export function AIInput({
  children,
  className,
  onSubmit,
  disabled = false,
  ...props
}: AIInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const trimmed = value.trim();
      if (!trimmed || disabled) return;
      onSubmit(trimmed);
      setValue("");
    },
    [value, disabled, onSubmit],
  );

  return (
    <AIInputContext.Provider value={{ value, setValue, disabled }}>
      <form
        onSubmit={handleSubmit}
        className={cn(
          "border-input bg-background flex items-end gap-2 rounded-xl border p-2 shadow-sm",
          "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
          className,
        )}
        {...props}
      >
        {children}
      </form>
    </AIInputContext.Provider>
  );
}

export type AIInputTextareaProps = Omit<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  "value" | "onChange"
>;

export function AIInputTextarea({
  className,
  placeholder = "Describe your booking request...",
  ...props
}: AIInputTextareaProps) {
  const { value, setValue, disabled } = useContext(AIInputContext);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const form = textareaRef.current?.closest("form");
        form?.requestSubmit();
      }
    },
    [],
  );

  return (
    <textarea
      ref={textareaRef}
      aria-label="Booking request"
      value={value}
      onChange={(e) => {
        setValue(e.target.value);
        adjustHeight();
      }}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      rows={1}
      className={cn(
        "placeholder:text-muted-foreground flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export type AIInputSubmitProps = HTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
};

export function AIInputSubmit({
  className,
  loading = false,
  ...props
}: AIInputSubmitProps) {
  const { value, disabled } = useContext(AIInputContext);
  const isDisabled = disabled || loading || !value.trim();

  return (
    <Button
      type="submit"
      size="icon"
      disabled={isDisabled}
      className={cn("shrink-0 rounded-lg", className)}
      {...props}
    >
      {loading ? (
        <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        <SendIcon className="size-4" />
      )}
    </Button>
  );
}

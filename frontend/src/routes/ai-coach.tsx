import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Send, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sendChat, type TokenUsage } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/ai-coach")({
  head: () => ({
    meta: [
      { title: "AI Coach — Garmin AI Trainer" },
      {
        name: "description",
        content: "Chat with your AI running coach about training load, recovery and pacing.",
      },
      { property: "og:title", content: "AI Coach — Garmin AI Trainer" },
      {
        property: "og:description",
        content: "Chat with your AI running coach about training load, recovery and pacing.",
      },
    ],
  }),
  component: AiCoach,
});

type Msg = { role: "user" | "assistant"; content: string; usage?: TokenUsage };

function AiCoach() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sessionTokens, setSessionTokens] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: sendChat,
    onSuccess: (result) => {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: result.content, usage: result.usage },
      ]);
      if (result.usage) {
        setSessionTokens((t) => t + result.usage!.total_tokens);
      }
    },
    onError: () =>
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry, I couldn't reach the coaching service." },
      ]),
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mutation.isPending]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || mutation.isPending) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    mutation.mutate({ message: text, history: messages });
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="border-b border-border px-4 py-4 md:px-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">AI Coach</h1>
            <p className="text-sm text-muted-foreground">Ask about training, recovery or pacing</p>
          </div>
          {sessionTokens > 0 && (
            <div className="text-right text-xs text-muted-foreground">
              <span className="font-medium">{sessionTokens.toLocaleString()}</span> tokens this session
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.length === 0 ? (
            <div className="mt-16 flex flex-col items-center text-center">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                <Zap className="size-6" />
              </span>
              <p className="mt-4 text-base font-medium">How can I help your training today?</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Try: "How should I structure next week?"
              </p>
            </div>
          ) : null}

          {messages.map((m, i) => (
            <div
              key={i}
              className={cn("flex flex-col", m.role === "user" ? "items-end" : "items-start")}
            >
              <div
                className={cn(
                  "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  m.role === "user"
                    ? "rounded-br-sm bg-primary text-primary-foreground"
                    : "rounded-bl-sm bg-muted text-foreground",
                )}
              >
                {m.content}
              </div>
              {m.usage && (
                <span className="mt-1 text-[11px] text-muted-foreground">
                  {m.usage.prompt_tokens}↑ {m.usage.completion_tokens}↓ = {m.usage.total_tokens} tokens
                </span>
              )}
            </div>
          ))}

          {mutation.isPending ? (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-2.5 text-sm text-muted-foreground">
                Coach is thinking…
              </div>
            </div>
          ) : null}
          <div ref={endRef} />
        </div>
      </div>

      <form onSubmit={onSubmit} className="border-t border-border p-4 md:px-6">
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message your AI coach…"
            className="h-11"
          />
          <Button type="submit" size="lg" disabled={!input.trim() || mutation.isPending}>
            <Send className="size-4" />
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}

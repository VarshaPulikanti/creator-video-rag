"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ChatMessage,
  type SourceCitation,
  streamChat,
} from "@/lib/api";

const PROMPTS = [
  "Why did Video A get more engagement than Video B?",
  "What's the engagement rate of each?",
  "Compare the hooks in the first 5 seconds.",
  "Who's the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A.",
];

interface Props {
  sessionId: string | null;
  disabled?: boolean;
}

export default function ChatPanel({ sessionId, disabled }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim() || loading) return;

      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text.trim(),
      };
      const assistantId = `a-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "", streaming: true },
      ]);
      setInput("");
      setLoading(true);

      let accumulated = "";
      let sources: SourceCitation[] = [];

      await streamChat(
        sessionId,
        text.trim(),
        (token) => {
          accumulated += token;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: accumulated, streaming: true }
                : m
            )
          );
        },
        (src) => {
          sources = src;
        },
        (full) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: full || accumulated,
                    sources,
                    streaming: false,
                  }
                : m
            )
          );
          setLoading(false);
        },
        (err) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: `Error: ${err}`,
                    streaming: false,
                  }
                : m
            )
          );
          setLoading(false);
        }
      );
    },
    [sessionId, loading]
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="chat-panel">
      <div className="messages">
        {!sessionId && (
          <p className="empty-state">
            Ingest two videos to start chatting. Answers stream live with source
            citations per chunk.
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`msg ${msg.role} ${msg.streaming ? "streaming" : ""}`}
          >
            {msg.content}
            {msg.sources && msg.sources.length > 0 && (
              <div className="citations">
                <h4>Sources</h4>
                {msg.sources.map((s, i) => (
                  <div className="cite-item" key={`${s.video_id}-${s.chunk_index}-${i}`}>
                    <strong>Video {s.video_id}</strong> · chunk {s.chunk_index} ·{" "}
                    {s.platform}
                    <br />
                    {s.excerpt}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {sessionId && (
        <div className="suggestions">
          {PROMPTS.map((p) => (
            <button
              key={p}
              type="button"
              disabled={disabled || loading}
              onClick={() => send(p)}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <form className="chat-input-row" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            sessionId ? "Ask about engagement, hooks, creators…" : "Ingest videos first"
          }
          disabled={!sessionId || disabled || loading}
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!sessionId || disabled || loading || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

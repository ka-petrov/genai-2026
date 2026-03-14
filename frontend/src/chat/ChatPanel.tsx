import { useEffect, useRef, useState } from "react";
import type { ChatMessage, RegionSpec } from "../types";
import { formatDistance } from "../map/geo";
import {
  PinIcon,
  SendIcon,
  ExpandIcon,
  CollapseIcon,
  CheckIcon,
} from "../ds";

interface Props {
  expanded: boolean;
  onToggleExpand: () => void;
  messages: ChatMessage[];
  onSend: (content: string) => void;
  isStreaming: boolean;
  streamingText: string;
  contextReady: boolean;
  isCreatingContext: boolean;
  region: RegionSpec | null;
  initialQuestion?: string;
}

export default function ChatPanel({
  expanded,
  onToggleExpand,
  messages,
  onSend,
  isStreaming,
  streamingText,
  contextReady,
  isCreatingContext,
  region,
  initialQuestion,
}: Props) {
  const [draft, setDraft] = useState(initialQuestion ?? "");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialQuestion) setDraft(initialQuestion);
  }, [initialQuestion]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingText]);

  const submit = () => {
    const text = draft.trim();
    if (!text || isStreaming || !contextReady) return;
    onSend(text);
    setDraft("");
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-raised">
      {/* ---- header ---- */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-default shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-lg font-bold text-fg tracking-tight shrink-0">
            GenGeo
          </h1>
          {region && (
            <span className="text-xs text-fg-muted truncate">
              {region.lat.toFixed(4)}, {region.lon.toFixed(4)} &middot;{" "}
              {formatDistance(region.radius_m)}
            </span>
          )}
        </div>

        <button
          onClick={onToggleExpand}
          className="p-1.5 rounded-md hover:bg-surface-sunken transition-colors text-fg-muted hover:text-fg shrink-0 cursor-pointer"
          title={expanded ? "Show map" : "Expand chat"}
        >
          {expanded ? <CollapseIcon /> : <ExpandIcon />}
        </button>
      </div>

      {/* ---- messages ---- */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {!contextReady && !isCreatingContext && <EmptyState />}
        {isCreatingContext && <CreatingState />}
        {contextReady && messages.length === 0 && !isStreaming && (
          <ReadyState />
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {isStreaming && streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl rounded-bl-md px-4 py-3 bg-bubble-assistant text-bubble-assistant-text text-sm leading-relaxed whitespace-pre-wrap">
              {streamingText}
              <span className="inline-block w-1.5 h-4 ml-0.5 bg-accent rounded-sm animate-pulse align-text-bottom" />
            </div>
          </div>
        )}

        {isStreaming && !streamingText && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-bubble-assistant">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-fg-muted rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-fg-muted rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-fg-muted rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ---- input ---- */}
      <div className="border-t border-border-default px-4 py-3 shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = Math.min(el.scrollHeight, 120) + "px";
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={
              contextReady
                ? "Ask about this neighborhood..."
                : "Select an area on the map first"
            }
            disabled={!contextReady || isStreaming}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-border-subtle bg-surface-overlay px-4 py-2.5 text-sm text-fg-secondary focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-transparent disabled:opacity-40 placeholder:text-fg-faint"
          />
          <button
            onClick={submit}
            disabled={!draft.trim() || isStreaming || !contextReady}
            className="shrink-0 w-10 h-10 rounded-xl bg-accent text-fg flex items-center justify-center hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-bubble-user text-bubble-user-text rounded-br-md"
            : "bg-bubble-assistant text-bubble-assistant-text rounded-bl-md"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 gap-4">
      <div className="w-16 h-16 rounded-2xl bg-accent-subtle flex items-center justify-center">
        <PinIcon className="w-8 h-8 text-accent-text" strokeWidth={1.5} />
      </div>
      <div>
        <p className="font-semibold text-fg">Select an area to analyze</p>
        <p className="text-sm text-fg-muted mt-1">
          Click on the map to drop a pin, then click again to set a search
          radius.
        </p>
      </div>
    </div>
  );
}

function CreatingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 gap-3">
      <div className="w-10 h-10 border-4 border-border-subtle border-t-accent rounded-full animate-spin" />
      <p className="text-sm text-fg-muted font-medium">
        Analyzing neighborhood...
      </p>
    </div>
  );
}

function ReadyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 gap-3">
      <div className="w-12 h-12 rounded-full bg-status-success-subtle flex items-center justify-center">
        <CheckIcon className="w-6 h-6 text-status-success" />
      </div>
      <div>
        <p className="font-semibold text-fg">Area ready!</p>
        <p className="text-sm text-fg-muted mt-1">
          Ask anything about this neighborhood &mdash; walkability, transit,
          family-friendliness, safety, and more.
        </p>
      </div>
    </div>
  );
}

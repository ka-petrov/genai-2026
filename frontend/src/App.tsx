import { useState, useCallback } from "react";
import MapView from "./map/MapView";
import ChatPanel from "./chat/ChatPanel";
import { createContext, streamChat } from "./api/client";
import {
  loadThreads,
  saveThreads,
  getActiveThreadId,
  setActiveThreadId,
  upsertThread,
} from "./storage";
import type {
  MapInteractionState,
  ChatThread,
  ChatMessage,
  RegionSpec,
} from "./types";

interface InitialState {
  threads: ChatThread[];
  activeThreadId: string | null;
  interaction: MapInteractionState;
  contextId: string | null;
}

function loadInitialState(): InitialState {
  const threads = loadThreads();
  const activeId = getActiveThreadId();
  const thread = activeId
    ? threads.find((t) => t.id === activeId)
    : undefined;
  return {
    threads,
    activeThreadId: activeId,
    interaction: thread
      ? {
          step: "radius_set" as const,
          lat: thread.region.lat,
          lon: thread.region.lon,
          radius_m: thread.region.radius_m,
        }
      : { step: "idle" as const },
    contextId: thread?.context_id ?? null,
  };
}

export default function App() {
  const [init] = useState(loadInitialState);

  const [threads, setThreads] = useState<ChatThread[]>(init.threads);
  const [activeThreadId, setActiveThreadIdLocal] = useState<string | null>(
    init.activeThreadId,
  );
  const [interaction, setInteraction] = useState<MapInteractionState>(
    init.interaction,
  );
  const [contextId, setContextId] = useState<string | null>(init.contextId);

  const [isCreatingContext, setIsCreatingContext] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [chatExpanded, setChatExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeThread =
    threads.find((t) => t.id === activeThreadId) ?? null;

  const persistActiveId = useCallback((id: string | null) => {
    setActiveThreadIdLocal(id);
    setActiveThreadId(id);
  }, []);

  // ---- map handlers ----

  const handlePinSet = useCallback((lat: number, lon: number) => {
    setInteraction({ step: "pin_set", lat, lon });
    setError(null);
  }, []);

  const handleRadiusSet = useCallback(
    async (lat: number, lon: number, radiusM: number) => {
      setInteraction({ step: "radius_set", lat, lon, radius_m: radiusM });
      setIsCreatingContext(true);
      setError(null);

      try {
        const ctx = await createContext({ lat, lon, radius_m: radiusM });
        setContextId(ctx.context_id);

        const thread: ChatThread = {
          id: crypto.randomUUID(),
          region: { lat, lon, radius_m: radiusM },
          context_id: ctx.context_id,
          messages: [],
          created_at: Date.now(),
        };

        setThreads((prev) => {
          const next = upsertThread(prev, thread);
          saveThreads(next);
          return next;
        });
        persistActiveId(thread.id);
      } catch (err) {
        console.error("Context creation failed:", err);
        setError("Failed to analyze area. Please try again.");
        setInteraction({ step: "idle" });
      } finally {
        setIsCreatingContext(false);
      }
    },
    [persistActiveId],
  );

  const handleReset = useCallback(() => {
    setInteraction({ step: "idle" });
    setContextId(null);
    persistActiveId(null);
    setError(null);
  }, [persistActiveId]);

  // ---- chat handler ----

  const handleSend = useCallback(
    async (content: string) => {
      if (!activeThread || !contextId || isStreaming) return;

      const userMsg: ChatMessage = { role: "user", content };
      const updatedMessages = [...activeThread.messages, userMsg];
      const updatedThread = { ...activeThread, messages: updatedMessages };

      setThreads((prev) => {
        const next = upsertThread(prev, updatedThread);
        saveThreads(next);
        return next;
      });

      setIsStreaming(true);
      setStreamingText("");
      setError(null);

      let fullText = "";

      try {
        for await (const event of streamChat(contextId, updatedMessages)) {
          if (event.event === "response.delta") {
            const text = (event.data as { text: string }).text;
            fullText += text;
            setStreamingText(fullText);
          } else if (event.event === "response.completed") {
            const data = event.data as { answer?: string };
            if (data.answer) fullText = data.answer;
          } else if (event.event === "response.error") {
            throw new Error(
              (event.data as { message?: string }).message ??
                "Stream error",
            );
          }
        }

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: fullText,
        };
        const finalMessages = [...updatedMessages, assistantMsg];
        const finalThread = { ...updatedThread, messages: finalMessages };

        setThreads((prev) => {
          const next = upsertThread(prev, finalThread);
          saveThreads(next);
          return next;
        });
      } catch (err) {
        console.error("Streaming failed:", err);
        setError("Response failed. Please try again.");
      } finally {
        setIsStreaming(false);
        setStreamingText("");
      }
    },
    [activeThread, contextId, isStreaming],
  );

  const region: RegionSpec | null =
    interaction.step === "radius_set"
      ? {
          lat: interaction.lat,
          lon: interaction.lon,
          radius_m: interaction.radius_m,
        }
      : null;

  return (
    <div className="flex h-full">
      <div
        className={`relative transition-[width] duration-200 ${
          chatExpanded ? "w-0 overflow-hidden" : "flex-1"
        }`}
      >
        <MapView
          interaction={interaction}
          onPinSet={handlePinSet}
          onRadiusSet={handleRadiusSet}
          onReset={handleReset}
          visible={!chatExpanded}
        />
      </div>

      <aside
        className={`flex flex-col border-l border-gray-200 transition-[width] duration-200 ${
          chatExpanded ? "flex-1" : "w-[420px]"
        }`}
      >
        <ChatPanel
          expanded={chatExpanded}
          onToggleExpand={() => setChatExpanded((v) => !v)}
          messages={activeThread?.messages ?? []}
          onSend={handleSend}
          isStreaming={isStreaming}
          streamingText={streamingText}
          contextReady={contextId !== null}
          isCreatingContext={isCreatingContext}
          region={region}
        />
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}
      </aside>
    </div>
  );
}

import { useCallback, useEffect, useRef } from "react";
import MapView from "../map/MapView";
import ChatPanel from "../chat/ChatPanel";
import { createContext, streamChat } from "../api/client";
import { useAppStore, useActiveThread } from "../store";
import type { ChatMessage, ChatThread } from "../types";

const DEFAULT_RADIUS = 800;

export default function MapPage() {
  const landing = useAppStore((s) => s.landing);
  const clearLanding = useAppStore((s) => s.clearLanding);

  const interaction = useAppStore((s) => s.interaction);
  const contextId = useAppStore((s) => s.contextId);
  const isCreatingContext = useAppStore((s) => s.isCreatingContext);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const streamingText = useAppStore((s) => s.streamingText);
  const chatExpanded = useAppStore((s) => s.chatExpanded);
  const error = useAppStore((s) => s.error);

  const setInteraction = useAppStore((s) => s.setInteraction);
  const setContextId = useAppStore((s) => s.setContextId);
  const createThread = useAppStore((s) => s.createThread);
  const appendMessage = useAppStore((s) => s.appendMessage);
  const setIsCreatingContext = useAppStore((s) => s.setIsCreatingContext);
  const setIsStreaming = useAppStore((s) => s.setIsStreaming);
  const setStreamingText = useAppStore((s) => s.setStreamingText);
  const setChatExpanded = useAppStore((s) => s.setChatExpanded);
  const setError = useAppStore((s) => s.setError);
  const resetStore = useAppStore((s) => s.reset);

  const activeThread = useActiveThread();

  const landingHandled = useRef(false);
  const pendingQuestion = useRef<string | null>(null);

  // ---- context creation ----
  const doCreateContext = useCallback(
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
        createThread(thread);
        return ctx.context_id;
      } catch (err) {
        console.error("Context creation failed:", err);
        setError("Failed to analyze area. Please try again.");
        setInteraction({ step: "idle" });
        return null;
      } finally {
        setIsCreatingContext(false);
      }
    },
    [setInteraction, setIsCreatingContext, setError, setContextId, createThread],
  );

  // ---- consume landing page input ----
  useEffect(() => {
    if (landingHandled.current || !landing) return;
    landingHandled.current = true;

    const { question, coords } = landing;

    if (contextId) {
      // Already have an active session — just queue the question
      pendingQuestion.current = question;
      clearLanding();
      return;
    }

    pendingQuestion.current = question;

    if (coords) {
      void doCreateContext(coords.lat, coords.lon, DEFAULT_RADIUS);
    }
    clearLanding();
  }, [landing, contextId, doCreateContext, clearLanding]);

  // ---- send a chat message ----
  const handleSend = useCallback(
    async (content: string) => {
      const store = useAppStore.getState();
      const thread = store.threads.find(
        (t) => t.id === store.activeThreadId,
      );
      const ctxId = store.contextId;
      if (!thread || !ctxId || store.isStreaming) return;

      const userMsg: ChatMessage = { role: "user", content };
      appendMessage(thread.id, userMsg);

      setIsStreaming(true);
      setStreamingText("");
      setError(null);

      const messagesForApi = [...thread.messages, userMsg];
      let fullText = "";

      try {
        for await (const event of streamChat(ctxId, messagesForApi)) {
          if (event.event === "response.delta") {
            const text = (event.data as { text: string }).text;
            fullText += text;
            setStreamingText(fullText);
          } else if (event.event === "response.completed") {
            const data = event.data as { answer?: string };
            if (data.answer) fullText = data.answer;
          } else if (event.event === "response.error") {
            throw new Error(
              (event.data as { message?: string }).message ?? "Stream error",
            );
          }
        }

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: fullText,
        };
        appendMessage(thread.id, assistantMsg);
      } catch (err) {
        console.error("Streaming failed:", err);
        setError("Response failed. Please try again.");
      } finally {
        setIsStreaming(false);
        setStreamingText("");
      }
    },
    [appendMessage, setIsStreaming, setStreamingText, setError],
  );

  // ---- auto-send pending question once context is ready ----
  useEffect(() => {
    if (
      !pendingQuestion.current ||
      !contextId ||
      !activeThread ||
      isStreaming ||
      isCreatingContext
    )
      return;
    const q = pendingQuestion.current;
    pendingQuestion.current = null;
    void handleSend(q);
  }, [contextId, activeThread, isStreaming, isCreatingContext, handleSend]);

  // ---- map handlers ----
  const handlePinSet = useCallback(
    (lat: number, lon: number) => {
      setInteraction({ step: "pin_set", lat, lon });
      setError(null);
    },
    [setInteraction, setError],
  );

  const handleRadiusSet = useCallback(
    async (lat: number, lon: number, radiusM: number) => {
      await doCreateContext(lat, lon, Math.max(50, radiusM));
    },
    [doCreateContext],
  );

  const handleReset = useCallback(() => {
    resetStore();
  }, [resetStore]);

  const region =
    interaction.step === "radius_set"
      ? {
          lat: interaction.lat,
          lon: interaction.lon,
          radius_m: interaction.radius_m,
        }
      : null;

  const flyTo =
    landing?.coords ??
    (interaction.step === "radius_set"
      ? { lat: interaction.lat, lon: interaction.lon }
      : undefined);

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
          flyToOnMount={flyTo ?? undefined}
        />
      </div>

      <aside
        className={`flex flex-col border-l border-gray-200 transition-[width] duration-200 ${
          chatExpanded ? "flex-1" : "w-[420px]"
        }`}
      >
        <ChatPanel
          expanded={chatExpanded}
          onToggleExpand={() => setChatExpanded(!chatExpanded)}
          messages={activeThread?.messages ?? []}
          onSend={handleSend}
          isStreaming={isStreaming}
          streamingText={streamingText}
          contextReady={contextId !== null}
          isCreatingContext={isCreatingContext}
          region={region}
          initialQuestion={pendingQuestion.current ?? undefined}
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

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatThread, ChatMessage, MapInteractionState } from "./types";

export interface LandingInput {
  question: string;
  address: string | null;
  coords: { lat: number; lon: number } | null;
}

interface PersistedSlice {
  threads: ChatThread[];
  activeThreadId: string | null;
  interaction: MapInteractionState;
  contextId: string | null;
  landing: LandingInput | null;
}

interface TransientSlice {
  isCreatingContext: boolean;
  isStreaming: boolean;
  streamingText: string;
  chatExpanded: boolean;
  error: string | null;
}

interface Actions {
  setLanding: (input: LandingInput) => void;
  clearLanding: () => void;

  setInteraction: (s: MapInteractionState) => void;
  setContextId: (id: string | null) => void;

  createThread: (thread: ChatThread) => void;
  setActiveThread: (id: string | null) => void;
  appendMessage: (threadId: string, msg: ChatMessage) => void;

  setIsCreatingContext: (v: boolean) => void;
  setIsStreaming: (v: boolean) => void;
  setStreamingText: (v: string) => void;
  setChatExpanded: (v: boolean) => void;
  setError: (v: string | null) => void;

  reset: () => void;
}

export type AppStore = PersistedSlice & TransientSlice & Actions;

function activeThread(state: PersistedSlice): ChatThread | null {
  if (!state.activeThreadId) return null;
  return state.threads.find((t) => t.id === state.activeThreadId) ?? null;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      // -- persisted --
      threads: [],
      activeThreadId: null,
      interaction: { step: "idle" },
      contextId: null,
      landing: null,

      // -- transient --
      isCreatingContext: false,
      isStreaming: false,
      streamingText: "",
      chatExpanded: false,
      error: null,

      // -- actions --
      setLanding: (input) => set({ landing: input }),
      clearLanding: () => set({ landing: null }),

      setInteraction: (s) => set({ interaction: s }),
      setContextId: (id) => set({ contextId: id }),

      createThread: (thread) =>
        set((state) => {
          const idx = state.threads.findIndex((t) => t.id === thread.id);
          if (idx >= 0) {
            const updated = [...state.threads];
            updated[idx] = thread;
            return { threads: updated, activeThreadId: thread.id };
          }
          return {
            threads: [...state.threads, thread],
            activeThreadId: thread.id,
          };
        }),

      setActiveThread: (id) => set({ activeThreadId: id }),

      appendMessage: (threadId, msg) =>
        set((state) => {
          const idx = state.threads.findIndex((t) => t.id === threadId);
          if (idx < 0) return state;
          const thread = state.threads[idx]!;
          const updated = [...state.threads];
          updated[idx] = { ...thread, messages: [...thread.messages, msg] };
          return { threads: updated };
        }),

      setIsCreatingContext: (v) => set({ isCreatingContext: v }),
      setIsStreaming: (v) => set({ isStreaming: v }),
      setStreamingText: (v) => set({ streamingText: v }),
      setChatExpanded: (v) => set({ chatExpanded: v }),
      setError: (v) => set({ error: v }),

      reset: () =>
        set({
          interaction: { step: "idle" },
          contextId: null,
          activeThreadId: null,
          error: null,
        }),
    }),
    {
      name: "gengeo-store",
      storage: {
        getItem: (name) => {
          const raw = sessionStorage.getItem(name);
          return raw ? JSON.parse(raw) : null;
        },
        setItem: (name, value) => {
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          sessionStorage.removeItem(name);
        },
      },
      partialize: (state) =>
        ({
          threads: state.threads,
          activeThreadId: state.activeThreadId,
          interaction: state.interaction,
          contextId: state.contextId,
          landing: state.landing,
        }) as unknown as AppStore,
    },
  ),
);

export function useActiveThread(): ChatThread | null {
  return useAppStore((s) => activeThread(s));
}

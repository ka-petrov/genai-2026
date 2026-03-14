import type { ChatThread } from "../types";

const THREADS_KEY = "gengeo_threads";
const ACTIVE_KEY = "gengeo_active_thread";

export function loadThreads(): ChatThread[] {
  try {
    const raw = sessionStorage.getItem(THREADS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ChatThread[];
  } catch {
    return [];
  }
}

export function saveThreads(threads: ChatThread[]): void {
  try {
    sessionStorage.setItem(THREADS_KEY, JSON.stringify(threads));
  } catch {
    console.warn("Failed to persist threads to sessionStorage");
  }
}

export function getActiveThreadId(): string | null {
  return sessionStorage.getItem(ACTIVE_KEY);
}

export function setActiveThreadId(id: string | null): void {
  if (id) {
    sessionStorage.setItem(ACTIVE_KEY, id);
  } else {
    sessionStorage.removeItem(ACTIVE_KEY);
  }
}

export function upsertThread(
  threads: ChatThread[],
  thread: ChatThread,
): ChatThread[] {
  const idx = threads.findIndex((t) => t.id === thread.id);
  if (idx >= 0) {
    const updated = [...threads];
    updated[idx] = thread;
    return updated;
  }
  return [...threads, thread];
}

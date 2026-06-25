/**
 * Hook that subscribes to the analysis-progress SSE stream and returns
 * the latest event for a given repository.
 *
 * Reconnects on transient network errors with exponential backoff.
 * Stops automatically once a terminal event arrives.
 */
import { useEffect, useRef, useState } from "react";

import { AnalysisApi } from "@/api/analysis";
import type { AnalysisProgressEvent } from "@/types/api";

export interface UseAnalysisProgressResult {
  event: AnalysisProgressEvent | null;
  connected: boolean;
  error: string | null;
}

const TERMINAL = new Set(["succeeded", "failed"]);

export function useAnalysisProgress(
  repositoryId: string | undefined,
  enabled = true,
): UseAnalysisProgressResult {
  const [event, setEvent] = useState<AnalysisProgressEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    if (!repositoryId || !enabled) return;
    cancelled.current = false;
    setEvent(null);
    setError(null);

    const controller = new AbortController();
    let attempt = 0;

    const run = async () => {
      while (!cancelled.current) {
        try {
          setConnected(true);
          for await (const evt of AnalysisApi.events(repositoryId, controller.signal)) {
            if (cancelled.current) break;
            setEvent(evt);
            if (TERMINAL.has(evt.event)) {
              cancelled.current = true;
              break;
            }
          }
          // Server closed the stream voluntarily — no need to reconnect.
          break;
        } catch (e) {
          if (cancelled.current) break;
          attempt += 1;
          setError((e as Error).message);
          setConnected(false);
          // Backoff: 0.5s, 1s, 2s, 4s, capped at 5s.
          const delay = Math.min(500 * 2 ** (attempt - 1), 5000);
          await new Promise((r) => setTimeout(r, delay));
        }
      }
      setConnected(false);
    };
    void run();

    return () => {
      cancelled.current = true;
      controller.abort();
    };
  }, [repositoryId, enabled]);

  return { event, connected, error };
}

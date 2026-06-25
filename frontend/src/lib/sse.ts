/**
 * Server-Sent Events client.
 *
 * Why not the native ``EventSource``? Because it's GET-only and the
 * backend's chat endpoint is POST. We implement a small fetch-based
 * streaming parser that handles both GET and POST and yields events
 * in the standard ``event: ...\\ndata: ...\\n\\n`` framing.
 */

export interface SseEvent {
  event: string;
  data: string;
  id?: string;
}

export interface OpenSseOptions {
  url: string;
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

/**
 * Open an SSE stream and async-iterate ``SseEvent`` objects.
 *
 * Throws on non-2xx response. Iteration ends when the server closes the
 * connection or the abort signal fires.
 */
export async function* openSse(options: OpenSseOptions): AsyncIterableIterator<SseEvent> {
  const { url, method = "GET", body, headers = {}, signal } = options;

  const response = await fetch(url, {
    method,
    headers: {
      Accept: "text/event-stream",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`SSE request failed: ${response.status} ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("SSE response has no body");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;

      // Spec: events are separated by blank lines (\n\n or \r\n\r\n).
      let separatorIndex = findEventSeparator(buffer);
      while (separatorIndex !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex).replace(/^(\r?\n)+/, "");
        const parsed = parseSseEvent(rawEvent);
        if (parsed) yield parsed;
        separatorIndex = findEventSeparator(buffer);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// helpers (exported for unit tests)
// ---------------------------------------------------------------------------
export function findEventSeparator(buffer: string): number {
  const idx1 = buffer.indexOf("\n\n");
  const idx2 = buffer.indexOf("\r\n\r\n");
  if (idx1 === -1) return idx2;
  if (idx2 === -1) return idx1;
  return Math.min(idx1, idx2);
}

export function parseSseEvent(raw: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  let id: string | undefined;

  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    const value = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");
    switch (field) {
      case "event":
        event = value;
        break;
      case "data":
        dataLines.push(value);
        break;
      case "id":
        id = value;
        break;
      default:
        // Unknown fields per spec are ignored.
        break;
    }
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n"), id };
}

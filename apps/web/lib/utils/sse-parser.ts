/**
 * Small utility to parse Server-Sent Events (SSE) from a fetch ReadableStream.
 * Converts raw text chunks into discrete { event, data } objects.
 */

export interface ParsedSSEEvent<T = unknown> {
  event: string;
  data: T;
}

/**
 * Parses an SSE stream by reading from the provided reader and invoking onEvent for each parsed message.
 */
export async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (evt: ParsedSSEEvent) => void,
  onError?: (err: Error) => void
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Split on double newlines (support both LF and CRLF)
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || '';

      for (const raw of parts) {
        const lines = raw.split(/\r?\n/);
        let eventType = 'message';
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            // Preserve payload as-is (no trim) while removing the 'data:' prefix and a single leading space if present
            const after = line.slice(5);
            dataLines.push(after.startsWith(' ') ? after.slice(1) : after);
          }
          // Ignore other SSE fields for now (id:, retry:)
        }

        const dataRaw = dataLines.join('\n');
        try {
          const data = dataRaw ? JSON.parse(dataRaw) : null;
          onEvent({ event: eventType, data });
        } catch {
          console.warn('Failed to parse SSE JSON payload:', dataRaw);
          onEvent({ event: eventType, data: dataRaw });
        }
      }
    }
  } catch (err) {
    if (onError && err instanceof Error) {
      onError(err);
      return;
    }
    throw err;
  } finally {
    try { await reader.cancel(); } catch {}
    try { reader.releaseLock(); } catch {}
  }
}

/**
 * Creates a fetch-based SSE connection and parses events via parseSSEStream.
 */
export async function createSSEConnection(
  url: string,
  options: RequestInit,
  onEvent: (evt: ParsedSSEEvent) => void,
  onError?: (err: Error) => void
): Promise<void> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`SSE connection failed [${response.status} ${response.statusText}]: ${text}`);
  }

  const body = response.body;
  if (!body) {
    throw new Error('SSE response has no body');
  }
  const reader = body.getReader();
  await parseSSEStream(reader, onEvent, onError);
}

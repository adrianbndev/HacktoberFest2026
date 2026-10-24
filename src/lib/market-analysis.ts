/**
 * Deep market analysis client (Phase 2, additive).
 *
 * `EventSource` cannot POST, so the SSE stream is consumed with `fetch` and a
 * `ReadableStream` reader. Both helpers forward the Firebase ID token, exactly
 * like `requestJson` in `src/lib/api.ts`.
 */

import { auth } from "@/lib/firebase";
import type {
  AnalysisErrorEvent,
  AnalysisStartedEvent,
  MarketAnalysisEvent,
  MarketAnalysisRecommendation,
  MarketAnalysisRequest,
  MarketAnalysisResult,
  MarketAnalysisValuation,
  MarketSourceResult,
  SourceStartedEvent,
} from "@/types/market-analysis";

const ANALYZE_PATH = "/api/market/analyze";
const STREAM_PATH = "/api/market/analyze/stream";

export class MarketAnalysisError extends Error {
  readonly status?: number;
  readonly sources?: Record<string, string>;

  constructor(detail: string, status?: number, sources?: Record<string, string>) {
    super(detail);
    this.name = "MarketAnalysisError";
    this.status = status;
    this.sources = sources;
  }
}

export interface StreamMarketAnalysisOptions {
  onEvent?: (event: MarketAnalysisEvent) => void;
  signal?: AbortSignal;
}

export async function analyzeMarket(
  request: MarketAnalysisRequest,
): Promise<MarketAnalysisResult> {
  const response = await fetch(ANALYZE_PATH, {
    method: "POST",
    headers: await jsonHeaders(),
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await readErrorPayload(response);
    throw new MarketAnalysisError(error.detail, response.status, error.sources);
  }
  return (await response.json()) as MarketAnalysisResult;
}

export async function streamMarketAnalysis(
  request: MarketAnalysisRequest,
  options: StreamMarketAnalysisOptions = {},
): Promise<MarketAnalysisResult> {
  const response = await fetch(STREAM_PATH, {
    method: "POST",
    headers: await jsonHeaders(),
    body: JSON.stringify(request),
    signal: options.signal,
  });
  if (!response.ok) {
    const error = await readErrorPayload(response);
    throw new MarketAnalysisError(error.detail, response.status, error.sources);
  }
  if (!response.body) {
    throw new MarketAnalysisError("stream_unavailable", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: MarketAnalysisResult | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseSseFrame(frame);
        if (event) {
          options.onEvent?.(event);
          if (event.type === "done") {
            result = event.data;
          } else if (event.type === "error") {
            await reader.cancel();
            throw new MarketAnalysisError(event.data.detail, response.status, event.data.sources);
          }
        }
        boundary = buffer.indexOf("\n\n");
      }
      if (done) {
        break;
      }
    }
    if (buffer.trim()) {
      const event = parseSseFrame(buffer);
      if (event?.type === "done") {
        result = event.data;
      } else if (event?.type === "error") {
        throw new MarketAnalysisError(event.data.detail, response.status, event.data.sources);
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!result) {
    throw new MarketAnalysisError("stream_ended_without_done", response.status);
  }
  return result;
}

/** Parse one SSE frame (`event:` + one or more `data:` lines). Comments return `null`. */
export function parseSseFrame(frame: string): MarketAnalysisEvent | null {
  let name = "";
  const dataLines: string[] = [];
  for (const rawLine of frame.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      name = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).replace(/^ /, ""));
    }
  }
  if (!name || dataLines.length === 0) return null;

  let data: unknown;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }

  switch (name) {
    case "analysis_started":
      return { type: name, data: data as AnalysisStartedEvent };
    case "source_started":
      return { type: name, data: data as SourceStartedEvent };
    case "source_result":
      return { type: name, data: data as MarketSourceResult };
    case "valuation":
      return { type: name, data: data as MarketAnalysisValuation };
    case "recommendation":
      return { type: name, data: data as MarketAnalysisRecommendation };
    case "done":
      return { type: name, data: data as MarketAnalysisResult };
    case "error":
      return { type: name, data: data as AnalysisErrorEvent };
    default:
      return null;
  }
}

async function jsonHeaders(): Promise<Record<string, string>> {
  const token = await auth.currentUser?.getIdToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function readErrorPayload(
  response: Response,
): Promise<{ detail: string; sources?: Record<string, string> }> {
  try {
    const payload: unknown = await response.json();
    if (isRecord(payload) && typeof payload.detail === "string") {
      const sources = isRecord(payload.sources)
        ? toStringRecord(payload.sources)
        : undefined;
      return { detail: payload.detail, sources };
    }
  } catch {
    // Non-JSON error body: fall back to the HTTP status.
  }
  return { detail: `HTTP ${response.status}` };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toStringRecord(value: Record<string, unknown>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, item] of Object.entries(value)) {
    if (typeof item === "string") {
      result[key] = item;
    }
  }
  return result;
}

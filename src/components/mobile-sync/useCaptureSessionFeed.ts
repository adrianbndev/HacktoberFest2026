"use client";

import { useEffect, useEffectEvent, useRef } from "react";
import { requestJson } from "@/lib/api";
import type { MobileCaptureSession } from "@/types/sdd";

const POLL_INTERVAL_MS = 1200; // .agent/rules/hackathon-guardrails.md §1.4

/**
 * Transporte de la sesión de captura: SSE en vivo con polling como red de seguridad.
 * Avisa solo cuando la sesión cambia, para que la pantalla del PC reaccione una única vez.
 */
export function useCaptureSessionFeed(
  sessionId: string | null | undefined,
  onSession: (session: MobileCaptureSession) => void,
) {
  const notify = useEffectEvent(onSession);
  const lastPayloadRef = useRef("");

  useEffect(() => {
    if (!sessionId) return;
    lastPayloadRef.current = "";
    const publish = (payload: string) => {
      if (payload === lastPayloadRef.current) return;
      lastPayloadRef.current = payload;
      notify(JSON.parse(payload) as MobileCaptureSession);
    };
    const source = new EventSource(`/api/capture-session/${sessionId}/stream`);
    source.addEventListener("session", (event) => {
      try {
        publish(event.data);
      } catch {
        // Un frame corrupto no debe romper el flujo: el polling de abajo reintenta.
      }
    });
    source.addEventListener("expired", () => source.close());
    return () => source.close();
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    let disposed = false;
    async function poll() {
      const session = await requestJson<MobileCaptureSession>(`/api/capture-session/${sessionId}`).catch(() => null);
      if (!session || disposed) return;
      const payload = JSON.stringify(session);
      if (payload === lastPayloadRef.current) return;
      lastPayloadRef.current = payload;
      notify(session);
    }
    void poll();
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [sessionId]);
}

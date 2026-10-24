"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import type {
  CaptureSessionCreated, CaptureSessionUpdate, InventoryItem, MarketValuationRequest, MarketValuationResult,
  MobileCaptureSession, TeamMemberId, VisionAnalysisResult, VisionAnalyzeRequest,
} from "@/types/sdd";

const POLL_INTERVAL_MS = 1200; // .agent/rules/hackathon-guardrails.md §1.4

export type CaptureStep = "waiting" | "connected" | "vision" | "market" | "done" | "error";

function buildInventoryItem(
  userId: TeamMemberId, photoUrl: string, vision: VisionAnalysisResult, valuation: MarketValuationResult,
): InventoryItem {
  const now = new Date().toISOString();
  const { priceMin, priceAvg, priceMax, sampleSize, platforms, comparableListings } = valuation;
  return {
    id: `item-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    userId, photoUrl,
    name: vision.name, category: vision.category, brand: vision.brand, model: vision.model,
    conditionScore: vision.conditionScore, conditionLabel: vision.conditionLabel,
    conditionReasoning: vision.conditionReasoning, seoTitle: vision.seoTitle, seoDescription: vision.seoDescription,
    priceMin, priceAvg, priceMax, priceTrend: "stable", priceDeltaPercent: 0, priceDeltaEur: 0,
    priceHistory: [{ timestamp: now, priceMin, priceAvg, priceMax, sampleSize, platforms }],
    comparableListings, status: "in_stock", createdAt: now, lastUpdatedAt: now,
  };
}

/** Sesión QR: espera la foto del móvil y la pasa por Visión IA -> MCP -> inventario sin tocar el teclado. */
export function useCaptureSession(userId: TeamMemberId, onItemCreated: (item: InventoryItem) => void) {
  const [session, setSession] = useState<CaptureSessionCreated | null>(null);
  const [step, setStep] = useState<CaptureStep>("waiting");
  const [photo, setPhoto] = useState<string | null>(null);
  const [item, setItem] = useState<InventoryItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    requestJson<CaptureSessionCreated>("/api/capture-session", "POST", { userId })
      .then((created) => !cancelled && setSession(created))
      .catch(() => !cancelled && setStep("error"));
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const processPhoto = useEffectEvent(async (sessionId: string, photoDataUrl: string) => {
    setPhoto(photoDataUrl);
    setStep("vision");
    try {
      const visionRequest: VisionAnalyzeRequest = { photoDataUrl };
      const vision = await requestJson<VisionAnalysisResult>("/api/vision/analyze", "POST", visionRequest);
      setStep("market");
      const valuationRequest: MarketValuationRequest = {
        query: vision.name, brand: vision.brand, model: vision.model, category: vision.category,
        conditionScore: vision.conditionScore, conditionLabel: vision.conditionLabel,
      };
      const valuation = await requestJson<MarketValuationResult>("/api/market/valuate", "POST", valuationRequest);
      const newItem = buildInventoryItem(userId, photoDataUrl, vision, valuation);
      await requestJson("/api/inventory", "POST", newItem);
      const completed: CaptureSessionUpdate = { status: "completed" };
      requestJson(`/api/capture-session/${sessionId}`, "PUT", completed).catch(() => undefined);
      setItem(newItem);
      setStep("done");
      onItemCreated(newItem);
    } catch {
      setStep("error");
    }
  });

  useEffect(() => {
    if (!session) return;
    let stopped = false;
    const timer = window.setInterval(async () => {
      const current = await requestJson<MobileCaptureSession>(`/api/capture-session/${session.sessionId}`).catch(
        () => null,
      );
      if (stopped || !current) return;
      if (current.status === "mobile_connected") setStep((previous) => (previous === "waiting" ? "connected" : previous));
      if (current.status === "photo_uploaded" && current.photoDataUrl) {
        stopped = true; // evita procesar dos veces si dos consultas llegan a la vez
        window.clearInterval(timer);
        processPhoto(session.sessionId, current.photoDataUrl);
      }
    }, POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [session]);

  /** Respaldo de la demo: sube una foto desde el PC a la misma sesión, como si llegara del móvil. */
  async function simulateCapture(file: File) {
    if (!session) return;
    const update: CaptureSessionUpdate = { status: "photo_uploaded", photoDataUrl: await compressImageFileToDataUrl(file) };
    await requestJson(`/api/capture-session/${session.sessionId}`, "PUT", update).catch(() => setStep("error"));
  }

  return { session, step, photo, item, simulateCapture };
}

"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import { formatDynamicFieldsSummary } from "@/lib/vision/category-fields";
import type {
  CaptureSessionCreated,
  CaptureSessionUpdate,
  InventoryItem,
  MarketValuationResult,
  MobileCaptureSession,
  TeamMemberId,
  ValuationRequest,
  VisionAnalysisResult,
  VisionAnalyzeRequest,
} from "@/types/sdd";

const POLL_INTERVAL_MS = 1200; // .agent/rules/hackathon-guardrails.md §1.4

export type CaptureStep = "waiting" | "connected" | "vision" | "review" | "market" | "done" | "error";

function buildInventoryItem(
  userId: TeamMemberId,
  photoUrl: string,
  vision: VisionAnalysisResult,
  valuation: MarketValuationResult,
  details?: string,
): InventoryItem {
  const now = new Date().toISOString();
  const { priceMin, priceAvg, priceMax, sampleSize, platforms, comparableListings } = valuation;
  return {
    id: `item-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    userId,
    photoUrl,
    name: vision.name,
    category: vision.category,
    brand: vision.brand,
    model: vision.model,
    conditionScore: vision.conditionScore,
    conditionLabel: vision.conditionLabel,
    conditionReasoning: vision.conditionReasoning,
    seoTitle: vision.seoTitle,
    seoDescription: vision.seoDescription,
    priceMin,
    priceAvg,
    priceMax,
    priceTrend: "stable",
    priceDeltaPercent: 0,
    priceDeltaEur: 0,
    priceHistory: [{ timestamp: now, priceMin, priceAvg, priceMax, sampleSize, platforms }],
    comparableListings,
    status: "in_stock",
    createdAt: now,
    lastUpdatedAt: now,
    details: details?.trim() || undefined,
  };
}

/**
 * Sesión QR: recibe la foto del móvil, muestra estado de carga mientras el modelo de Visión IA
 * extrae los datos + campos dinámicos, presenta el formulario editable (`review`) y, tras confirmar, tasa y guarda.
 */
export function useCaptureSession(userId: TeamMemberId, onItemCreated: (item: InventoryItem) => void) {
  const [session, setSession] = useState<CaptureSessionCreated | null>(null);
  const [step, setStep] = useState<CaptureStep>("waiting");
  const [photo, setPhoto] = useState<string | null>(null);
  const [visionDraft, setVisionDraft] = useState<VisionAnalysisResult | null>(null);
  const [item, setItem] = useState<InventoryItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    requestJson<CaptureSessionCreated>("/api/capture-session", "POST")
      .then((created) => !cancelled && setSession(created))
      .catch(() => !cancelled && setStep("error"));
    return () => {
      cancelled = true;
    };
  }, [userId]);

  async function analyzePhotoWithModel(sessionId: string, photoDataUrl: string, userHint?: string) {
    setPhoto(photoDataUrl);
    setVisionDraft(null);
    setItem(null);
    setStep("vision");
    const analyzingUpdate: CaptureSessionUpdate = { status: "analyzing" };
    requestJson(`/api/capture-session/${sessionId}`, "PUT", analyzingUpdate).catch(() => undefined);

    try {
      const visionRequest: VisionAnalyzeRequest = { photoDataUrl, userHint };
      const vision = await requestJson<VisionAnalysisResult>("/api/vision/analyze", "POST", visionRequest);
      setVisionDraft(vision);
      setStep("review");
      const readyForReview: CaptureSessionUpdate = { status: "completed" };
      requestJson(`/api/capture-session/${sessionId}`, "PUT", readyForReview).catch(() => undefined);
    } catch {
      setStep("error");
      const failedUpdate: CaptureSessionUpdate = { status: "error" };
      requestJson(`/api/capture-session/${sessionId}`, "PUT", failedUpdate).catch(() => undefined);
    }
  }

  const onPolledPhoto = useEffectEvent((sessionId: string, photoDataUrl: string) =>
    analyzePhotoWithModel(sessionId, photoDataUrl),
  );

  useEffect(() => {
    if (!session) return;
    let busy = false;
    const timer = window.setInterval(async () => {
      if (busy) return;
      const current = await requestJson<MobileCaptureSession>(`/api/capture-session/${session.sessionId}`).catch(
        () => null,
      );
      if (!current) return;
      if (current.status === "mobile_connected") {
        setStep((prev) => (prev === "waiting" ? "connected" : prev));
      }
      if (current.status === "photo_uploaded" && current.photoDataUrl) {
        busy = true;
        await onPolledPhoto(session.sessionId, current.photoDataUrl);
        busy = false;
      }
    }, POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, [session]);

  async function confirmVisionAndValuate(adjustedVision: VisionAnalysisResult, extraNotes = "") {
    if (!session || !photo) return;
    setVisionDraft(adjustedVision);
    setStep("market");
    try {
      const dynamicSummary = formatDynamicFieldsSummary(adjustedVision.dynamicFields ?? [], extraNotes);
      const valuationRequest: ValuationRequest = {
        query: adjustedVision.name,
        brand: adjustedVision.brand,
        model: adjustedVision.model,
        category: adjustedVision.category,
        conditionScore: adjustedVision.conditionScore,
        conditionLabel: adjustedVision.conditionLabel,
      };
      const valuation = await requestJson<MarketValuationResult>("/api/market/valuate", "POST", valuationRequest);
      const newItem = buildInventoryItem(userId, photo, adjustedVision, valuation, dynamicSummary);
      await requestJson("/api/inventory", "POST", newItem);
      const completed: CaptureSessionUpdate = { status: "completed" };
      requestJson(`/api/capture-session/${session.sessionId}`, "PUT", completed).catch(() => undefined);
      setItem(newItem);
      setStep("done");
      onItemCreated(newItem);
    } catch {
      setStep("error");
    }
  }

  async function simulateCapture(file: File, userHint?: string) {
    if (!session) return;
    try {
      const photoDataUrl = await compressImageFileToDataUrl(file);
      await analyzePhotoWithModel(session.sessionId, photoDataUrl, userHint);
    } catch {
      setStep("error");
    }
  }

  function resetToCapture() {
    setPhoto(null);
    setVisionDraft(null);
    setItem(null);
    setStep("waiting");
    if (session) {
      const resetUpdate: CaptureSessionUpdate = { status: "waiting_for_mobile" };
      requestJson(`/api/capture-session/${session.sessionId}`, "PUT", resetUpdate).catch(() => undefined);
    }
  }

  async function saveDetails(details: string) {
    if (!item) return;
    const updated: InventoryItem = { ...item, details: details.trim() || undefined };
    await requestJson("/api/inventory", "POST", updated);
    setItem(updated);
    onItemCreated(updated);
  }

  return {
    session,
    step,
    photo,
    visionDraft,
    item,
    simulateCapture,
    confirmVisionAndValuate,
    resetToCapture,
    saveDetails,
  };
}

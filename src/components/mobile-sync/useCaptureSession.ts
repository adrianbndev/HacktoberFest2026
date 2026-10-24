"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import { formatDynamicFieldsSummary } from "@/lib/vision/category-fields";
import type {
  CaptureSessionCreated,
  CaptureSessionStatus,
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
const PC_BUSY_EVENT = "lifeos:pc-busy";
const REVIEW_BUSY_REASON =
  "Se está terminando de añadir el producto anterior en el portátil (revisando los datos). Guárdalo o cierra la ventana en el PC para sacar otra foto.";
const MARKET_BUSY_REASON =
  "Tasando y guardando el producto anterior en el portátil. Espera unos segundos…";

export type CaptureStep = "waiting" | "connected" | "vision" | "review" | "market" | "done" | "error";

export interface UseCaptureSessionOptions {
  onOpenModal?: () => void;
  externalBusyReason?: string | null;
}

export function setLaptopBusyReason(reason: string | null) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent<string | null>(PC_BUSY_EVENT, { detail: reason }));
  }
}

function putSessionState(sessionId: string, status: CaptureSessionStatus, busyReason: string | null = null) {
  const body: CaptureSessionUpdate = { status, busyReason };
  return requestJson(`/api/capture-session/${sessionId}`, "PUT", body).catch(() => undefined);
}

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

export function useCaptureSession(
  userId: TeamMemberId,
  onItemCreated: (item: InventoryItem) => void,
  options?: UseCaptureSessionOptions,
) {
  const [session, setSession] = useState<CaptureSessionCreated | null>(null);
  const [step, setStep] = useState<CaptureStep>("waiting");
  const [photo, setPhoto] = useState<string | null>(null);
  const [visionDraft, setVisionDraft] = useState<VisionAnalysisResult | null>(null);
  const [item, setItem] = useState<InventoryItem | null>(null);
  const [eventBusyReason, setEventBusyReason] = useState<string | null>(null);
  const runIdRef = useRef(0);
  const prevExternalBusyRef = useRef<string | null>(null);
  const activeExternalBusyReason = options?.externalBusyReason ?? eventBusyReason;

  useEffect(() => {
    const handler = (event: Event) => setEventBusyReason((event as CustomEvent<string | null>).detail ?? null);
    window.addEventListener(PC_BUSY_EVENT, handler);
    return () => window.removeEventListener(PC_BUSY_EVENT, handler);
  }, []);

  useEffect(() => {
    let cancelled = false;
    requestJson<CaptureSessionCreated>("/api/capture-session", "POST")
      .then((created) => !cancelled && setSession(created))
      .catch(() => !cancelled && setStep("error"));
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    if (!session || prevExternalBusyRef.current === activeExternalBusyReason) return;
    prevExternalBusyRef.current = activeExternalBusyReason;
    if (step === "vision" || step === "review" || step === "market") return;
    void putSessionState(session.sessionId, step === "done" ? "completed" : "mobile_connected", activeExternalBusyReason);
  }, [session, activeExternalBusyReason, step]);

  async function analyzePhotoWithModel(sessionId: string, photoDataUrl: string, userHint?: string) {
    const runId = ++runIdRef.current;
    setPhoto(photoDataUrl);
    setVisionDraft(null);
    setItem(null);
    setStep("vision");
    await putSessionState(sessionId, "analyzing", null);
    try {
      const visionRequest: VisionAnalyzeRequest = { photoDataUrl, userHint };
      const vision = await requestJson<VisionAnalysisResult>("/api/vision/analyze", "POST", visionRequest);
      if (runIdRef.current !== runId) return;
      setVisionDraft(vision);
      setStep("review");
      await putSessionState(sessionId, "mobile_connected", REVIEW_BUSY_REASON);
    } catch {
      if (runIdRef.current !== runId) return;
      setStep("error");
      await putSessionState(sessionId, "error", null);
    }
  }

  const onPolledPhoto = useEffectEvent(async (sessionId: string, photoDataUrl: string) => {
    if (activeExternalBusyReason || step === "vision" || step === "review" || step === "market") return;
    options?.onOpenModal?.();
    await analyzePhotoWithModel(sessionId, photoDataUrl);
  });

  useEffect(() => {
    if (!session) return;
    let busy = false;
    async function pollSession() {
      if (busy || !session) return;
      const current = await requestJson<MobileCaptureSession>(`/api/capture-session/${session.sessionId}`).catch(
        () => null,
      );
      if (!current) return;
      if (current.status === "mobile_connected" || current.status === "completed") {
        setStep((prev) => (prev === "waiting" ? "connected" : prev));
      }
      if (current.status === "photo_uploaded" && current.photoDataUrl) {
        busy = true;
        await onPolledPhoto(session.sessionId, current.photoDataUrl);
        busy = false;
      }
    }
    void pollSession();
    const timer = window.setInterval(pollSession, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [session]);

  async function confirmVisionAndValuate(adjustedVision: VisionAnalysisResult, extraNotes = "") {
    if (!session || !photo) return;
    const runId = ++runIdRef.current;
    setVisionDraft(adjustedVision);
    setStep("market");
    await putSessionState(session.sessionId, "mobile_connected", MARKET_BUSY_REASON);
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
      if (runIdRef.current !== runId) return;
      const newItem = buildInventoryItem(userId, photo, adjustedVision, valuation, dynamicSummary);
      await requestJson("/api/inventory", "POST", newItem);
      if (runIdRef.current !== runId) return;
      await putSessionState(session.sessionId, "completed", activeExternalBusyReason ?? null);
      setItem(newItem);
      setStep("done");
      onItemCreated(newItem);
    } catch {
      if (runIdRef.current !== runId) return;
      setStep("error");
      await putSessionState(session.sessionId, "error", null);
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

  function clearCurrentCapture(nextStatus: CaptureSessionStatus) {
    runIdRef.current += 1;
    setPhoto(null);
    setVisionDraft(null);
    setItem(null);
    setStep((prev) => (prev === "waiting" ? "waiting" : "connected"));
    if (session) void putSessionState(session.sessionId, nextStatus, activeExternalBusyReason ?? null);
  }

  return {
    session,
    step,
    photo,
    visionDraft,
    item,
    simulateCapture,
    confirmVisionAndValuate,
    resetToCapture: () => clearCurrentCapture("mobile_connected"),
    handleModalClose: () => clearCurrentCapture(step === "done" ? "completed" : "mobile_connected"),
  };
}

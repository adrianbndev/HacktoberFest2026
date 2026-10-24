"use client";

import { useEffect, useRef, useState } from "react";
import { requestJson } from "@/lib/api";
import { MarketAnalysisError, streamMarketAnalysis } from "@/lib/market-analysis";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import { formatDynamicFieldsSummary } from "@/lib/vision/category-fields";
import { buildInventoryItem, upsertSourceResult } from "./capture-item";
import { useCaptureSessionFeed } from "./useCaptureSessionFeed";
import type {
  MarketAnalysisRecommendation,
  MarketSourceResult,
} from "@/types/market-analysis";
import type {
  CaptureSessionCreated,
  CaptureSessionStatus,
  CaptureSessionUpdate,
  InventoryItem,
  TeamMemberId,
  VisionAnalysisResult,
  VisionAnalyzeRequest,
} from "@/types/sdd";
import { visionToMarketAnalysis } from "./vision-to-market";

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
  const [marketSources, setMarketSources] = useState<MarketSourceResult[]>([]);
  const [marketRecommendation, setMarketRecommendation] = useState<MarketAnalysisRecommendation | null>(null);
  const [marketWarnings, setMarketWarnings] = useState<string[]>([]);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [eventBusyReason, setEventBusyReason] = useState<string | null>(null);
  const runIdRef = useRef(0);
  const lastPhotoRef = useRef<string | null>(null);
  const marketAbortRef = useRef<AbortController | null>(null);
  const prevExternalBusyRef = useRef<string | null>(null);
  const activeExternalBusyReason = options?.externalBusyReason ?? eventBusyReason;

  function abortMarketAnalysis() {
    marketAbortRef.current?.abort();
    marketAbortRef.current = null;
  }

  function resetMarketState() {
    setMarketSources([]);
    setMarketRecommendation(null);
    setMarketWarnings([]);
    setMarketError(null);
  }

  useEffect(() => () => marketAbortRef.current?.abort(), []);

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
    abortMarketAnalysis();
    resetMarketState();
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

  async function onPolledPhoto(sessionId: string, photoDataUrl: string) {
    if (activeExternalBusyReason || step === "vision" || step === "review" || step === "market") return;
    if (lastPhotoRef.current === photoDataUrl) return; // SSE y polling pueden entregar la misma foto
    lastPhotoRef.current = photoDataUrl;
    options?.onOpenModal?.();
    await analyzePhotoWithModel(sessionId, photoDataUrl);
  }

  useCaptureSessionFeed(session?.sessionId, (current) => {
    if (current.status === "mobile_connected" || current.status === "completed") {
      setStep((prev) => (prev === "waiting" ? "connected" : prev));
    }
    if (current.status === "photo_uploaded" && current.photoDataUrl) {
      void onPolledPhoto(current.sessionId, current.photoDataUrl);
    }
  });

  async function confirmVisionAndValuate(adjustedVision: VisionAnalysisResult, extraNotes = "") {
    if (!session || !photo) return;
    const runId = ++runIdRef.current;
    abortMarketAnalysis();
    const controller = new AbortController();
    marketAbortRef.current = controller;
    setVisionDraft(adjustedVision);
    resetMarketState();
    setStep("market");
    await putSessionState(session.sessionId, "mobile_connected", MARKET_BUSY_REASON);
    try {
      const dynamicSummary = formatDynamicFieldsSummary(adjustedVision.dynamicFields ?? [], extraNotes);
      const analysis = await streamMarketAnalysis(visionToMarketAnalysis(adjustedVision), {
        signal: controller.signal,
        onEvent: (event) => {
          if (runIdRef.current !== runId) return;
          if (event.type === "source_result") {
            setMarketSources((prev) => upsertSourceResult(prev, event.data));
          } else if (event.type === "recommendation") {
            setMarketRecommendation(event.data);
          } else if (event.type === "done") {
            setMarketSources(event.data.sources);
            setMarketRecommendation(event.data.recommendation ?? null);
            setMarketWarnings(event.data.warnings);
          }
        },
      });
      if (controller.signal.aborted || runIdRef.current !== runId) return;
      setMarketSources(analysis.sources);
      setMarketRecommendation(analysis.recommendation ?? null);
      setMarketWarnings(analysis.warnings);
      const newItem = buildInventoryItem(userId, photo, adjustedVision, analysis, dynamicSummary);
      await requestJson("/api/inventory", "POST", newItem);
      if (runIdRef.current !== runId) return;
      await putSessionState(session.sessionId, "completed", activeExternalBusyReason ?? null);
      setItem(newItem);
      setStep("done");
      onItemCreated(newItem);
    } catch (error) {
      if (controller.signal.aborted || runIdRef.current !== runId) return;
      setMarketError(
        error instanceof MarketAnalysisError
          ? error.message
          : "No hemos podido guardar el producto con los precios del análisis.",
      );
      setStep("error");
      await putSessionState(session.sessionId, "error", null);
    } finally {
      if (marketAbortRef.current === controller) marketAbortRef.current = null;
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
    lastPhotoRef.current = null;
    abortMarketAnalysis();
    resetMarketState();
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
    marketSources,
    marketRecommendation,
    marketWarnings,
    marketError,
    simulateCapture,
    confirmVisionAndValuate,
    resetToCapture: () => clearCurrentCapture("mobile_connected"),
    handleModalClose: () => clearCurrentCapture(step === "done" ? "completed" : "mobile_connected"),
  };
}

"use client";

import type { RefObject } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Check, CircleCheck, Loader2, RotateCcw, TriangleAlert, Upload } from "lucide-react";
import { HealthScoreBadge } from "@/components/inventory/HealthScoreBadge";
import type { MarketAnalysisRecommendation, MarketSourceResult } from "@/types/market-analysis";
import type { CaptureSessionCreated, InventoryItem, VisionAnalysisResult } from "@/types/sdd";
import { MarketProgress } from "./MarketProgress";

export const SECONDARY_BUTTON =
  "flex h-11 items-center justify-center gap-2 rounded-full bg-fog px-5 text-[15px] font-semibold transition-colors hover:bg-fog-2 disabled:opacity-50";

interface ErrorPanelProps {
  marketError: string | null;
  sources: MarketSourceResult[];
  warnings: string[];
  visionDraft: VisionAnalysisResult | null;
  onRetry: (vision: VisionAnalysisResult) => void;
  onReset: () => void;
}

export function CaptureErrorPanel({ marketError, sources, warnings, visionDraft, onRetry, onReset }: ErrorPanelProps) {
  if (!marketError) {
    return (
      <div className="flex flex-col gap-3">
        <p role="alert" className="flex items-center gap-3 rounded-inner bg-rose-50 p-4 text-[15px] text-rose-800">
          <TriangleAlert className="size-5 shrink-0" aria-hidden />
          No hemos podido analizar la foto. Prueba con otra, con buena luz y el objeto entero a la vista.
        </p>
        <button type="button" onClick={onReset} className={SECONDARY_BUTTON}>
          <RotateCcw className="size-4" aria-hidden /> Volver a intentarlo
        </button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <MarketProgress
        sources={sources}
        warnings={warnings}
        error={marketError}
        onRetry={visionDraft ? () => onRetry(visionDraft) : undefined}
      />
      <button type="button" onClick={onReset} className={SECONDARY_BUTTON}>
        <RotateCcw className="size-4" aria-hidden /> Usar otra foto
      </button>
    </div>
  );
}

interface WaitingPanelProps {
  session: CaptureSessionCreated | null;
  mobileUrl: string;
  baseUrl: string;
  connected: boolean;
  fileRef: RefObject<HTMLInputElement | null>;
  onBaseUrlChange: (value: string) => void;
  onUpload: () => void;
  onFile: (file: File) => void;
}

export function CaptureWaitingPanel({
  session,
  mobileUrl,
  baseUrl,
  connected,
  fileRef,
  onBaseUrlChange,
  onUpload,
  onFile,
}: WaitingPanelProps) {
  return (
    <div className="flex flex-col items-center gap-5">
      <div className="grid size-56 place-items-center rounded-panel bg-paper p-3 ring-1 ring-line">
        {session ? (
          <QRCodeSVG value={mobileUrl} size={200} marginSize={1} bgColor="#ffffff" fgColor="#101114" />
        ) : (
          <Loader2 className="size-8 animate-spin text-ink-2" aria-label="Creando sesión" />
        )}
      </div>
      <p role="status" className={`text-center text-[15px] font-semibold ${connected ? "text-accent" : ""}`}>
        {connected ? "Móvil conectado: haz la foto cuando quieras" : "Escanea el código con la cámara del móvil"}
      </p>
      <label className="w-full text-[13px] font-medium text-ink-2">
        Dirección que abre el móvil (cámbiala si usas un túnel o el hotspot)
        <input
          value={baseUrl}
          onChange={(event) => onBaseUrlChange(event.target.value)}
          className="mt-1.5 h-11 w-full rounded-inner border border-line bg-paper px-3.5 text-[15px] text-ink transition-colors focus:border-accent"
        />
      </label>
      <button type="button" disabled={!session} onClick={onUpload} className={`${SECONDARY_BUTTON} w-full`}>
        <Upload className="size-4" aria-hidden /> Subir una foto desde este ordenador
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </div>
  );
}

interface DonePanelProps {
  item: InventoryItem;
  sources: MarketSourceResult[];
  recommendation: MarketAnalysisRecommendation | null;
  warnings: string[];
  onReset: () => void;
}

export function CaptureDonePanel({ item, sources, recommendation, warnings, onReset }: DonePanelProps) {
  return (
    <>
      <p role="status" className="flex items-center gap-2 text-[15px] font-semibold">
        <CircleCheck className="size-5 text-accent" aria-hidden /> Guardado en tu inventario
      </p>
      <div>
        <p className="text-lg font-semibold">{item.name}</p>
        <p className="text-sm text-ink-2">
          {item.brand} · {item.model} · {item.category}
        </p>
      </div>
      <HealthScoreBadge score={item.conditionScore} label={item.conditionLabel} reasoning={item.conditionReasoning} />
      {item.details && (
        <div className="whitespace-pre-line rounded-inner bg-fog p-3.5 text-sm leading-relaxed text-ink-2">
          {item.details}
        </div>
      )}
      <MarketProgress
        sources={sources}
        recommendation={recommendation}
        warnings={warnings}
        prices={{ priceMin: item.priceMin, priceAvg: item.priceAvg, priceMax: item.priceMax }}
        complete
      />
      <div className="flex gap-2.5">
        <button type="button" onClick={onReset} className={SECONDARY_BUTTON}>
          <RotateCcw className="size-4" aria-hidden /> Tasar otro
        </button>
        <form method="dialog" className="flex-1">
          <button className="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-accent text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover">
            <Check className="size-4" aria-hidden /> Hecho
          </button>
        </form>
      </div>
    </>
  );
}

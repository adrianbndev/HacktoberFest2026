"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Check, CircleCheck, Loader2, RotateCcw, ScanSearch, Smartphone, TriangleAlert, Upload, X } from "lucide-react";
import { HealthScoreBadge } from "@/components/inventory/HealthScoreBadge";
import type { InventoryItem, TeamMemberId } from "@/types/sdd";
import { DynamicProductForm } from "./DynamicProductForm";
import { MarketProgress } from "./MarketProgress";
import { ZoomablePhoto } from "@/components/ui/ZoomablePhoto";
import { useDialogScrollLock } from "@/components/ui/useDialogScrollLock";
import { useCaptureSession } from "./useCaptureSession";

export interface MobileSyncModalProps {
  userId: TeamMemberId;
  isOpen: boolean;
  onOpen?: () => void;
  onClose: () => void;
  onItemCreated: (newItem: InventoryItem) => void;
  busyReason?: string | null;
}

const SECONDARY_BUTTON =
  "flex h-11 items-center justify-center gap-2 rounded-full bg-fog px-5 text-[15px] font-semibold transition-colors hover:bg-fog-2 disabled:opacity-50";

// Si el PC usa localhost, el QR apunta a la IP de la red local que detecta el backend.
function defaultBaseUrl(mobileUrl: string) {
  const { hostname, origin } = window.location;
  return hostname === "localhost" || hostname === "127.0.0.1" ? new URL(mobileUrl).origin : origin;
}

export function MobileSyncModal({ userId, isOpen, onOpen, onClose, onItemCreated, busyReason }: MobileSyncModalProps) {
  const capture = useCaptureSession(userId, onItemCreated, {
    onOpenModal: onOpen,
    externalBusyReason: busyReason,
  });

  if (!isOpen) return null;

  return (
    <MobileSyncDialog
      capture={capture}
      onClose={() => {
        capture.handleModalClose();
        onClose();
      }}
    />
  );
}

function MobileSyncDialog({
  capture,
  onClose,
}: {
  capture: ReturnType<typeof useCaptureSession>;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [customBaseUrl, setCustomBaseUrl] = useState<string | null>(null);
  const {
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
    resetToCapture,
  } = capture;

  useEffect(() => dialogRef.current?.showModal(), []);
  useDialogScrollLock(dialogRef);

  const baseUrl = customBaseUrl ?? (session ? defaultBaseUrl(session.mobileUrl) : "");
  const mobileUrl = session ? `${baseUrl.replace(/\/+$/, "")}/mobile-capture/${session.sessionId}` : "";
  const waiting = step === "waiting" || step === "connected";
  // Con foto (análisis, revisión, resultado) el modal se ensancha: foto arriba y los datos a todo el ancho.
  const wide = !waiting && step !== "error";

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="mobile-sync-title"
      className={`m-auto max-h-[92dvh] overflow-y-auto overscroll-contain rounded-panel bg-paper p-6 text-ink backdrop:bg-black/55 backdrop:backdrop-blur-sm sm:p-7 ${
        wide ? "w-[min(95vw,56rem)]" : "w-[min(95vw,38rem)]"
      }`}
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <h2 id="mobile-sync-title" className="flex items-center gap-2.5 text-lg font-semibold">
          <Smartphone className="size-5" aria-hidden />
          {step === "review" ? "Revisa los datos del objeto" : "Tasar un objeto con el móvil"}
        </h2>
        <form method="dialog">
          <button aria-label="Cerrar" className="grid size-9 place-items-center rounded-full transition-colors hover:bg-fog">
            <X className="size-5" aria-hidden />
          </button>
        </form>
      </div>

      {step === "error" ? (
        <div className="flex flex-col gap-3">
          {marketError ? (
            <>
              <MarketProgress
                sources={marketSources}
                warnings={marketWarnings}
                error={marketError}
                onRetry={visionDraft ? () => void confirmVisionAndValuate(visionDraft) : undefined}
              />
              <button type="button" onClick={resetToCapture} className={SECONDARY_BUTTON}>
                <RotateCcw className="size-4" aria-hidden /> Usar otra foto
              </button>
            </>
          ) : (
            <>
              <p role="alert" className="flex items-center gap-3 rounded-inner bg-rose-50 p-4 text-[15px] text-rose-800">
                <TriangleAlert className="size-5 shrink-0" aria-hidden />
                No hemos podido analizar la foto. Prueba con otra, con buena luz y el objeto entero a la vista.
              </p>
              <button type="button" onClick={resetToCapture} className={SECONDARY_BUTTON}>
                <RotateCcw className="size-4" aria-hidden /> Volver a intentarlo
              </button>
            </>
          )}
        </div>
      ) : waiting ? (
        <div className="flex flex-col items-center gap-5">
          <div className="grid size-56 place-items-center rounded-panel bg-paper p-3 ring-1 ring-line">
            {session ? (
              <QRCodeSVG value={mobileUrl} size={200} marginSize={1} bgColor="#ffffff" fgColor="#101114" />
            ) : (
              <Loader2 className="size-8 animate-spin text-ink-2" aria-label="Creando sesión" />
            )}
          </div>
          <p role="status" className={`text-center text-[15px] font-semibold ${step === "connected" ? "text-accent" : ""}`}>
            {step === "connected" ? "Móvil conectado: haz la foto cuando quieras" : "Escanea el código con la cámara del móvil"}
          </p>
          <label className="w-full text-[13px] font-medium text-ink-2">
            Dirección que abre el móvil (cámbiala si usas un túnel o el hotspot)
            <input
              value={baseUrl}
              onChange={(event) => setCustomBaseUrl(event.target.value)}
              className="mt-1.5 h-11 w-full rounded-inner border border-line bg-paper px-3.5 text-[15px] text-ink transition-colors focus:border-accent"
            />
          </label>
          <button
            type="button"
            disabled={!session}
            onClick={() => fileRef.current?.click()}
            className={`${SECONDARY_BUTTON} w-full`}
          >
            <Upload className="size-4" aria-hidden /> Subir una foto desde este ordenador
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) simulateCapture(file);
              event.target.value = "";
            }}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          {photo && (
            <div className="relative overflow-hidden rounded-inner bg-fog">
              <ZoomablePhoto src={photo} alt="Foto recibida del producto" className="h-auto max-h-80 w-full object-cover object-center sm:max-h-[30rem]">
                {step === "vision" && (
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-ink/45">
                    <div className="flex items-center gap-2.5 rounded-full bg-paper px-4 py-2 text-[13px] font-semibold text-ink">
                      <Loader2 className="size-4 animate-spin text-accent" aria-hidden />
                      Analizando la foto…
                    </div>
                  </div>
                )}
              </ZoomablePhoto>
            </div>
          )}

          <div className="flex min-w-0 flex-col gap-5">
            {step === "vision" && (
              <div role="status" aria-live="polite" className="flex flex-col gap-1.5 rounded-inner bg-fog p-4">
                <p className="flex items-center gap-2.5 text-[15px] font-semibold">
                  <ScanSearch className="size-5 text-accent" aria-hidden />
                  Reconociendo el objeto y su estado…
                </p>
                <p className="text-sm leading-relaxed text-ink-2">
                  Identificamos qué es, en qué estado está y qué datos pedirte según su tipo (móvil, consola, mueble…).
                </p>
              </div>
            )}

            {step === "review" && visionDraft && (
              <DynamicProductForm
                initialAnalysis={visionDraft}
                submitting={false}
                onConfirm={confirmVisionAndValuate}
                onRetake={resetToCapture}
              />
            )}

            {step === "market" && (
              <MarketProgress
                sources={marketSources}
                recommendation={marketRecommendation}
                warnings={marketWarnings}
              />
            )}

            {step === "done" && item && (
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
                <HealthScoreBadge
                  score={item.conditionScore}
                  label={item.conditionLabel}
                  reasoning={item.conditionReasoning}
                />
                {item.details && (
                  <div className="whitespace-pre-line rounded-inner bg-fog p-3.5 text-sm leading-relaxed text-ink-2">
                    {item.details}
                  </div>
                )}
                <MarketProgress
                  sources={marketSources}
                  recommendation={marketRecommendation}
                  warnings={marketWarnings}
                  prices={{ priceMin: item.priceMin, priceAvg: item.priceAvg, priceMax: item.priceMax }}
                  complete
                />
                <div className="flex gap-2.5">
                  <button type="button" onClick={resetToCapture} className={SECONDARY_BUTTON}>
                    <RotateCcw className="size-4" aria-hidden /> Tasar otro
                  </button>
                  <form method="dialog" className="flex-1">
                    <button className="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-accent text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover">
                      <Check className="size-4" aria-hidden /> Hecho
                    </button>
                  </form>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}

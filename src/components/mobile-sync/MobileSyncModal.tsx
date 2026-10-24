"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, ScanSearch, Smartphone, X } from "lucide-react";
import type { InventoryItem, TeamMemberId } from "@/types/sdd";
import { CaptureDonePanel, CaptureErrorPanel, CaptureWaitingPanel } from "./CapturePanels";
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
        <CaptureErrorPanel
          marketError={marketError}
          sources={marketSources}
          warnings={marketWarnings}
          visionDraft={visionDraft}
          onRetry={(vision) => void confirmVisionAndValuate(vision)}
          onReset={resetToCapture}
        />
      ) : waiting ? (
        <CaptureWaitingPanel
          session={session}
          mobileUrl={mobileUrl}
          baseUrl={baseUrl}
          connected={step === "connected"}
          fileRef={fileRef}
          onBaseUrlChange={setCustomBaseUrl}
          onUpload={() => fileRef.current?.click()}
          onFile={(file) => void simulateCapture(file)}
        />
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
              <CaptureDonePanel
                item={item}
                sources={marketSources}
                recommendation={marketRecommendation}
                warnings={marketWarnings}
                onReset={resetToCapture}
              />
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Check, FlaskConical, Loader2, RotateCcw, Smartphone, Sparkles, TriangleAlert, X } from "lucide-react";
import { HealthScoreBadge } from "@/components/inventory/HealthScoreBadge";
import { PriceTrioDisplay } from "@/components/inventory/PriceTrioDisplay";
import type { InventoryItem, TeamMemberId } from "@/types/sdd";
import { DynamicProductForm } from "./DynamicProductForm";
import { useCaptureSession } from "./useCaptureSession";

export interface MobileSyncModalProps {
  userId: TeamMemberId;
  isOpen: boolean;
  onClose: () => void;
  onItemCreated: (newItem: InventoryItem) => void;
}

// Si el PC usa localhost, el QR apunta a la IP de la red local que detecta el backend.
function defaultBaseUrl(mobileUrl: string) {
  const { hostname, origin } = window.location;
  return hostname === "localhost" || hostname === "127.0.0.1" ? new URL(mobileUrl).origin : origin;
}

export function MobileSyncModal({ isOpen, ...props }: MobileSyncModalProps) {
  return isOpen ? <MobileSyncDialog {...props} /> : null;
}

function MobileSyncDialog({ userId, onClose, onItemCreated }: Omit<MobileSyncModalProps, "isOpen">) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [customBaseUrl, setCustomBaseUrl] = useState<string | null>(null);
  const {
    session,
    step,
    photo,
    visionDraft,
    item,
    simulateCapture,
    confirmVisionAndValuate,
    resetToCapture,
  } = useCaptureSession(userId, onItemCreated);

  useEffect(() => dialogRef.current?.showModal(), []);

  const baseUrl = customBaseUrl ?? (session ? defaultBaseUrl(session.mobileUrl) : "");
  const mobileUrl = session ? `${baseUrl.replace(/\/+$/, "")}/mobile-capture/${session.sessionId}` : "";
  const waiting = step === "waiting" || step === "connected";

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="mobile-sync-title"
      className="m-auto max-h-[92dvh] w-[min(95vw,38rem)] overflow-y-auto rounded-3xl bg-white p-6 text-zinc-900 backdrop:bg-black/60 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <h2 id="mobile-sync-title" className="flex items-center gap-2 text-lg font-semibold">
          <Smartphone className="size-5" aria-hidden />
          {step === "review" ? "Revisar datos del producto" : "Añadir producto con el móvil"}
        </h2>
        <form method="dialog">
          <button aria-label="Cerrar" className="rounded-full p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800">
            <X className="size-5" aria-hidden />
          </button>
        </form>
      </div>

      {step === "error" ? (
        <div className="flex flex-col gap-3">
          <p
            role="alert"
            className="flex items-center gap-3 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300"
          >
            <TriangleAlert className="size-5 shrink-0" aria-hidden />
            No se pudo completar el análisis de la imagen. Inténtalo de nuevo con otra foto.
          </p>
          <button
            type="button"
            onClick={resetToCapture}
            className="flex items-center justify-center gap-2 rounded-2xl border border-zinc-200 py-2.5 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            <RotateCcw className="size-4" aria-hidden /> Volver a intentar
          </button>
        </div>
      ) : waiting ? (
        <div className="flex flex-col items-center gap-4">
          <div className="grid size-56 place-items-center rounded-3xl bg-white p-3 ring-1 ring-zinc-200">
            {session ? (
              <QRCodeSVG value={mobileUrl} size={200} marginSize={1} bgColor="#ffffff" fgColor="#18181b" />
            ) : (
              <Loader2 className="size-8 animate-spin text-zinc-400" aria-label="Creando sesión" />
            )}
          </div>
          <p role="status" className="text-center text-sm font-medium">
            {step === "connected" ? "📱 ¡Móvil conectado! Esperando foto…" : "Escanea el QR con la cámara del móvil"}
          </p>
          <label className="w-full text-xs text-zinc-500 dark:text-zinc-400">
            Dirección para el móvil (cámbiala si usas un túnel o el hotspot)
            <input
              value={baseUrl}
              onChange={(event) => setCustomBaseUrl(event.target.value)}
              className="mt-1 w-full rounded-xl border border-zinc-200 bg-transparent px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:text-zinc-100"
            />
          </label>
          <button
            type="button"
            disabled={!session}
            onClick={() => fileRef.current?.click()}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-zinc-200 py-2.5 text-sm font-medium transition hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            <FlaskConical className="size-4" aria-hidden /> Subir o simular foto desde este dispositivo
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
        <div className="flex flex-col gap-4">
          {photo && (
            <div className="relative overflow-hidden rounded-2xl bg-zinc-100 dark:bg-zinc-800">
              {/* eslint-disable-next-line @next/next/no-img-element -- foto recibida en data URL */}
              <img
                src={photo}
                alt="Foto recibida del producto"
                className={`${step === "review" ? "max-h-48" : "aspect-[4/3]"} w-full object-cover`}
              />
              {step === "vision" && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/45 backdrop-blur-[2px]">
                  <div className="flex items-center gap-2.5 rounded-full bg-white/95 px-4 py-2 text-xs font-semibold text-zinc-900 shadow-lg">
                    <Loader2 className="size-4 animate-spin text-emerald-600" aria-hidden />
                    Analizando imagen con el modelo IA…
                  </div>
                </div>
              )}
            </div>
          )}

          {step === "vision" && (
            <div
              role="status"
              aria-live="polite"
              className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-800/50"
            >
              <div className="flex items-center gap-2.5 text-sm font-semibold">
                <Sparkles className="size-4 animate-pulse text-emerald-600 dark:text-emerald-400" aria-hidden />
                Procesando fotografía en el modelo de Visión IA…
              </div>
              <p className="text-xs leading-relaxed text-zinc-600 dark:text-zinc-300">
                Estamos identificando el producto, su estado físico y generando los campos dinámicos específicos según su categoría (ej. móvil, vehículo, consola, mobiliario…).
              </p>
            </div>
          )}

          {(step === "review" || step === "market") && visionDraft && (
            <DynamicProductForm
              initialAnalysis={visionDraft}
              submitting={step === "market"}
              onConfirm={confirmVisionAndValuate}
              onRetake={resetToCapture}
            />
          )}

          {step === "done" && item && (
            <>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{item.category}</p>
                <p className="text-lg font-semibold">{item.name}</p>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  {item.brand} · {item.model}
                </p>
              </div>
              <HealthScoreBadge
                score={item.conditionScore}
                label={item.conditionLabel}
                reasoning={item.conditionReasoning}
              />
              {item.details && (
                <div className="whitespace-pre-line rounded-2xl bg-zinc-100 p-3.5 text-xs leading-relaxed text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  {item.details}
                </div>
              )}
              <PriceTrioDisplay priceMin={item.priceMin} priceAvg={item.priceAvg} priceMax={item.priceMax} />
              <div className="flex gap-2.5">
                <button
                  type="button"
                  onClick={resetToCapture}
                  className="flex items-center justify-center gap-1.5 rounded-2xl border border-zinc-200 px-4 py-3 text-xs font-semibold hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
                >
                  <RotateCcw className="size-4" aria-hidden /> Subir otro
                </button>
                <form method="dialog" className="flex-1">
                  <button className="flex w-full items-center justify-center gap-2 rounded-2xl bg-zinc-900 py-3 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900">
                    <Check className="size-4" aria-hidden /> Guardado en Mi Inventario
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      )}
    </dialog>
  );
}

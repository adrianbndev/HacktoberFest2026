"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Check, FlaskConical, Loader2, Smartphone, TriangleAlert, X } from "lucide-react";
import { HealthScoreBadge } from "@/components/inventory/HealthScoreBadge";
import { PriceTrioDisplay } from "@/components/inventory/PriceTrioDisplay";
import type { InventoryItem, TeamMemberId } from "@/types/sdd";
import { useCaptureSession, type CaptureStep } from "./useCaptureSession";

export interface MobileSyncModalProps {
  userId: TeamMemberId;
  isOpen: boolean;
  onClose: () => void;
  onItemCreated: (newItem: InventoryItem) => void;
}

const PIPELINE_STEPS = [
  "📸 Imagen recibida desde el móvil",
  "🔍 Evaluando estado y salud del producto con Visión IA",
  "🕵️ Consultando Wallapop, Vinted y Milanuncios vía MCP Stealth",
  "✅ Tasación completada",
];
const STEP_INDEX: Partial<Record<CaptureStep, number>> = { vision: 1, market: 2, done: 4 };

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
  const { session, step, photo, item, simulateCapture, saveDetails } = useCaptureSession(userId, onItemCreated);

  useEffect(() => dialogRef.current?.showModal(), []);

  const baseUrl = customBaseUrl ?? (session ? defaultBaseUrl(session.mobileUrl) : "");
  const mobileUrl = session ? `${baseUrl.replace(/\/+$/, "")}/mobile-capture/${session.sessionId}` : "";
  const waiting = step === "waiting" || step === "connected";

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="mobile-sync-title"
      className="m-auto w-[min(94vw,30rem)] rounded-3xl bg-white p-6 text-zinc-900 backdrop:bg-black/60 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <h2 id="mobile-sync-title" className="flex items-center gap-2 text-lg font-semibold">
          <Smartphone className="size-5" aria-hidden /> Añadir producto con el móvil
        </h2>
        <form method="dialog">
          <button aria-label="Cerrar" className="rounded-full p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800">
            <X className="size-5" aria-hidden />
          </button>
        </form>
      </div>

      {step === "error" ? (
        <p role="alert" className="flex items-center gap-3 rounded-2xl bg-rose-50 p-4 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
          <TriangleAlert className="size-5 shrink-0" aria-hidden /> No se pudo completar la tasación. Cierra y vuelve a intentarlo.
        </p>
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
            <FlaskConical className="size-4" aria-hidden /> Simular captura subiendo una foto desde el PC
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
            // eslint-disable-next-line @next/next/no-img-element -- foto recibida en data URL
            <img src={photo} alt="Foto recibida del móvil" className="aspect-[4/3] w-full rounded-2xl object-cover" />
          )}
          {step === "done" && item ? (
            <>
              <div>
                <p className="text-lg font-semibold">{item.name}</p>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{item.brand} · {item.model}</p>
              </div>
              <HealthScoreBadge score={item.conditionScore} label={item.conditionLabel} reasoning={item.conditionReasoning} />
              <PriceTrioDisplay priceMin={item.priceMin} priceAvg={item.priceAvg} priceMax={item.priceMax} />
              <ProductDetailsField onSave={saveDetails} />
              <form method="dialog">
                <button className="flex w-full items-center justify-center gap-2 rounded-2xl bg-zinc-900 py-3 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900">
                  <Check className="size-4" aria-hidden /> Guardado en Mi Inventario
                </button>
              </form>
            </>
          ) : (
            <ol className="flex flex-col gap-2" aria-live="polite">
              {PIPELINE_STEPS.map((label, index) => {
                const current = STEP_INDEX[step] ?? 0;
                const state = index < current ? "done" : index === current ? "active" : "pending";
                return (
                  <li key={label} className={`flex items-center gap-2 text-sm ${state === "pending" ? "opacity-40" : ""}`}>
                    {state === "active" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Check className="size-4" aria-hidden />}
                    {label}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </dialog>
  );
}

function ProductDetailsField({ onSave }: { onSave: (details: string) => Promise<void> }) {
  const [details, setDetails] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">("idle");

  async function save() {
    setState("saving");
    try {
      await onSave(details);
      setState("saved");
    } catch {
      setState("failed");
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="product-details" className="text-sm font-medium">
        Detalles para identificarlo mejor
      </label>
      <textarea
        id="product-details"
        value={details}
        onChange={(event) => {
          setDetails(event.target.value);
          setState("idle");
        }}
        rows={3}
        maxLength={2000}
        placeholder="Modelo exacto, capacidad, accesorios incluidos, defectos que no se ven en la foto…"
        className="w-full rounded-xl border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
      />
      <button
        type="button"
        onClick={save}
        disabled={!details.trim() || state === "saving" || state === "saved"}
        className="self-end rounded-xl border border-zinc-200 px-3 py-1.5 text-sm font-medium transition hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
      >
        {state === "saved" ? "Detalles guardados" : state === "saving" ? "Guardando…" : "Guardar detalles"}
      </button>
      {state === "failed" && (
        <p role="alert" className="text-xs text-rose-600">No se pudieron guardar los detalles. Vuelve a intentarlo.</p>
      )}
    </div>
  );
}

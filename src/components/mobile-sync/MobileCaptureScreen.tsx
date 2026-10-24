"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Camera, CheckCircle2, Loader2, RotateCcw, Sparkles, TriangleAlert } from "lucide-react";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import type { CaptureSessionUpdate, MobileCaptureSession } from "@/types/sdd";

type Phase = "connecting" | "ready" | "sending" | "analyzing" | "completed" | "expired" | "failed";

export function MobileCaptureScreen() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sessionUrl = `/api/capture-session/${sessionId}`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("connecting");
  const [preview, setPreview] = useState<string | null>(null);

  // Al abrir el QR avisamos al PC para que muestre "Móvil conectado".
  useEffect(() => {
    requestJson<MobileCaptureSession>(sessionUrl)
      .then((session) => {
        if (session.status !== "waiting_for_mobile") return setPhase("ready");
        const update: CaptureSessionUpdate = { status: "mobile_connected" };
        return requestJson(sessionUrl, "PUT", update).then(() => setPhase("ready"));
      })
      .catch(() => setPhase("expired"));
  }, [sessionUrl]);

  // Mientras el PC analiza la imagen con el modelo de Visión IA, escuchamos cuándo termina.
  useEffect(() => {
    if (phase !== "analyzing") return;
    const timer = window.setInterval(async () => {
      const current = await requestJson<MobileCaptureSession>(sessionUrl).catch(() => null);
      if (!current) return;
      if (current.status === "completed") {
        window.clearInterval(timer);
        setPhase("completed");
      } else if (current.status === "error") {
        window.clearInterval(timer);
        setPhase("failed");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [phase, sessionUrl]);

  async function sendPhoto(file: File) {
    setPhase("sending");
    try {
      const photoDataUrl = await compressImageFileToDataUrl(file);
      setPreview(photoDataUrl);
      const update: CaptureSessionUpdate = { status: "photo_uploaded", photoDataUrl };
      await requestJson(sessionUrl, "PUT", update);
      setPhase("analyzing");
    } catch {
      setPhase("failed");
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-6 p-6">
      <header>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">LifeOS · ReCommerce AI</p>
        <h1 className="text-2xl font-semibold">Añadir producto</h1>
      </header>

      {preview && (
        <div className="relative overflow-hidden rounded-3xl">
          {/* eslint-disable-next-line @next/next/no-img-element -- vista previa local en data URL */}
          <img src={preview} alt="Foto enviada" className="aspect-square w-full object-cover" />
          {(phase === "sending" || phase === "analyzing") && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/45 backdrop-blur-[2px]">
              <div className="flex items-center gap-2.5 rounded-full bg-white/95 px-4 py-2 text-xs font-semibold text-zinc-900 shadow-lg">
                <Loader2 className="size-4 animate-spin text-emerald-600" aria-hidden />
                {phase === "sending" ? "Subiendo foto…" : "Analizando con IA…"}
              </div>
            </div>
          )}
        </div>
      )}

      {phase === "connecting" && <Status icon={Loader2} spin text="Conectando con el PC…" />}
      {phase === "expired" && (
        <Status icon={TriangleAlert} text="Este código QR ya no es válido. Genera uno nuevo en el PC." />
      )}
      {phase === "sending" && <Status icon={Loader2} spin text="Enviando fotografía comprimida al PC…" />}
      {phase === "analyzing" && (
        <Status
          icon={Sparkles}
          spin
          text="Analizando la foto con el modelo de Visión IA para rellenar los campos dinámicos en la web…"
        />
      )}
      {phase === "completed" && (
        <>
          <Status
            icon={CheckCircle2}
            text="¡Información extraída! Revisa y edita el formulario dinámico en la pantalla del PC."
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-auto flex items-center justify-center gap-2 rounded-3xl border border-zinc-300 py-4 text-base font-semibold transition active:scale-[0.98] dark:border-zinc-700"
          >
            <RotateCcw className="size-5" aria-hidden /> Hacer otra foto
          </button>
        </>
      )}
      {phase === "failed" && <Status icon={TriangleAlert} text="No se pudo procesar la foto. Prueba otra vez." />}

      {(phase === "ready" || phase === "failed") && (
        <>
          <p className="text-zinc-600 dark:text-zinc-300">
            Haz una foto al producto con buena luz. El modelo de IA detectará el tipo de objeto y rellenará sus campos dinámicos en la web.
          </p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-auto flex items-center justify-center gap-3 rounded-3xl bg-zinc-900 py-6 text-lg font-semibold text-white active:scale-[0.98] dark:bg-white dark:text-zinc-900"
          >
            <Camera className="size-7" aria-hidden /> Hacer foto al producto
          </button>
        </>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) sendPhoto(file);
          event.target.value = "";
        }}
      />
    </main>
  );
}

function Status({ icon: Icon, text, spin }: { icon: typeof Camera; text: string; spin?: boolean }) {
  return (
    <p role="status" className="flex items-center gap-3 rounded-2xl bg-zinc-100 p-4 text-sm dark:bg-zinc-900">
      <Icon className={`size-6 shrink-0 ${spin ? "animate-spin" : ""}`} aria-hidden /> {text}
    </p>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Camera, CheckCircle2, Loader2, TriangleAlert } from "lucide-react";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import type { CaptureSessionUpdate, MobileCaptureSession } from "@/types/sdd";

type Phase = "connecting" | "ready" | "sending" | "sent" | "expired" | "failed";

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

  async function sendPhoto(file: File) {
    setPhase("sending");
    try {
      const photoDataUrl = await compressImageFileToDataUrl(file);
      setPreview(photoDataUrl);
      const update: CaptureSessionUpdate = { status: "photo_uploaded", photoDataUrl };
      await requestJson(sessionUrl, "PUT", update);
      setPhase("sent");
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
        // eslint-disable-next-line @next/next/no-img-element -- vista previa local en data URL
        <img src={preview} alt="Foto enviada" className="aspect-square w-full rounded-3xl object-cover" />
      )}

      {phase === "connecting" && <Status icon={Loader2} spin text="Conectando con el PC…" />}
      {phase === "expired" && <Status icon={TriangleAlert} text="Este código QR ya no es válido. Genera uno nuevo en el PC." />}
      {phase === "sending" && <Status icon={Loader2} spin text="Enviando la foto al PC…" />}
      {phase === "sent" && <Status icon={CheckCircle2} text="¡Foto enviada al PC! Mira la pantalla de tu ordenador." />}
      {phase === "failed" && <Status icon={TriangleAlert} text="No se pudo enviar la foto. Prueba otra vez." />}

      {(phase === "ready" || phase === "failed") && (
        <>
          <p className="text-zinc-600 dark:text-zinc-300">
            Haz una foto al producto con buena luz y que se vea entero. La IA calculará su estado y su precio.
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
    <p role="status" className="flex items-center gap-3 rounded-2xl bg-zinc-100 p-4 dark:bg-zinc-900">
      <Icon className={`size-6 shrink-0 ${spin ? "animate-spin" : ""}`} aria-hidden /> {text}
    </p>
  );
}

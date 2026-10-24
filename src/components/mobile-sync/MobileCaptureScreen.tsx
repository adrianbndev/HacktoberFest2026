"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Camera, CircleCheck, Clock, Loader2, RotateCcw, TriangleAlert } from "lucide-react";
import { Brand } from "@/components/dashboard/Brand";
import { requestJson } from "@/lib/api";
import { compressImageFileToDataUrl } from "@/lib/mobile-sync/image-compressor";
import type { CaptureSessionUpdate, MobileCaptureSession } from "@/types/sdd";

type Phase = "connecting" | "ready" | "sending" | "analyzing" | "busy" | "completed" | "expired" | "failed";

const POLL_INTERVAL_MS = 1200;
const PRIMARY_BUTTON =
  "mt-auto flex h-16 items-center justify-center gap-3 rounded-full bg-accent text-lg font-semibold text-white transition-transform active:scale-[0.98]";

export function MobileCaptureScreen() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sessionUrl = `/api/capture-session/${sessionId}`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("connecting");
  const [preview, setPreview] = useState<string | null>(null);
  const [busyReason, setBusyReason] = useState<string | null>(null);
  const pollEpochRef = useRef(0);
  const awaitingUntilRef = useRef(0);

  const applySessionState = useCallback(
    (current: MobileCaptureSession) => {
      if (Date.now() < awaitingUntilRef.current) {
        if (current.status === "analyzing" || current.busyReason || current.status === "error") {
          awaitingUntilRef.current = 0;
        } else {
          setPhase("sending");
          return;
        }
      }
      if (current.status === "waiting_for_mobile") {
        const update: CaptureSessionUpdate = { status: "mobile_connected", busyReason: null };
        void requestJson(sessionUrl, "PUT", update).catch(() => undefined);
        setBusyReason(null);
        setPhase("ready");
        return;
      }
      if (current.busyReason) {
        setBusyReason(current.busyReason);
        setPhase("busy");
        return;
      }
      setBusyReason(null);
      if (current.status === "photo_uploaded") {
        setPhase("sending");
      } else if (current.status === "analyzing") {
        setPhase("analyzing");
      } else if (current.status === "completed") {
        setPhase("completed");
      } else if (current.status === "error") {
        setPhase("failed");
      } else {
        setPhase("ready");
      }
    },
    [sessionUrl],
  );

  // Sincronización inicial al abrir o recargar la página móvil.
  useEffect(() => {
    const epoch = pollEpochRef.current;
    requestJson<MobileCaptureSession>(sessionUrl)
      .then((current) => {
        if (pollEpochRef.current === epoch) applySessionState(current);
      })
      .catch(() => setPhase("expired"));
  }, [sessionUrl, applySessionState]);

  // Escucha continua del estado del portátil (detecta si está ocupado añadiendo/editando o si ya guardó en la Home).
  useEffect(() => {
    if (phase === "connecting" || phase === "expired") return;
    const timer = window.setInterval(async () => {
      const epoch = pollEpochRef.current;
      const current = await requestJson<MobileCaptureSession>(sessionUrl).catch(() => null);
      if (current && pollEpochRef.current === epoch) applySessionState(current);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [phase, sessionUrl, applySessionState]);

  async function sendPhoto(file: File) {
    pollEpochRef.current += 1;
    awaitingUntilRef.current = Date.now() + 6000;
    setPhase("sending");
    try {
      const photoDataUrl = await compressImageFileToDataUrl(file);
      setPreview(photoDataUrl);
      const update: CaptureSessionUpdate = { status: "photo_uploaded", photoDataUrl, busyReason: null };
      await requestJson(sessionUrl, "PUT", update);
    } catch {
      awaitingUntilRef.current = 0;
      const current = await requestJson<MobileCaptureSession>(sessionUrl).catch(() => null);
      if (current && (current.busyReason || current.status === "analyzing")) {
        applySessionState(current);
      } else {
        setPhase("failed");
      }
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-6 bg-paper p-6 text-ink">
      <header className="flex flex-col gap-8">
        <Brand />
        <h1 className="font-display text-3xl font-semibold tracking-[-0.03em]">Tasar un objeto</h1>
      </header>

      {preview && (
        <div className="relative overflow-hidden rounded-panel bg-fog">
          {/* eslint-disable-next-line @next/next/no-img-element -- vista previa local en data URL */}
          <img src={preview} alt="Foto enviada" className="aspect-square w-full object-cover" />
          {(phase === "sending" || phase === "analyzing") && (
            <div className="absolute inset-0 flex items-center justify-center bg-ink/45">
              <div className="flex items-center gap-2.5 rounded-full bg-paper px-4 py-2 text-[13px] font-semibold text-ink shadow-[0_8px_24px_-8px_rgb(16_17_20/0.4)]">
                <Loader2 className="size-4 animate-spin text-accent" aria-hidden />
                {phase === "sending" ? "Cargando foto…" : "Analizando con IA…"}
              </div>
            </div>
          )}
        </div>
      )}

      {phase === "connecting" && <Status icon={Loader2} spin text="Conectando con el ordenador…" />}
      {phase === "expired" && (
        <Status icon={TriangleAlert} text="Este código QR ya no vale. Genera uno nuevo en el ordenador." />
      )}
      {phase === "sending" && <Status icon={Loader2} spin text="Cargando y enviando la foto al ordenador…" />}
      {phase === "analyzing" && (
        <Status icon={Loader2} spin text="Analizando la foto. Sigue en el ordenador para revisar los datos." />
      )}

      {phase === "busy" && (
        <>
          <div role="alert" className="flex flex-col gap-1.5 rounded-inner bg-amber-50 p-4 text-amber-900">
            <p className="flex items-center gap-2 font-semibold">
              <TriangleAlert className="size-5 shrink-0 text-amber-700" aria-hidden />
              Ahora no se puede hacer otra foto
            </p>
            <p className="text-sm leading-relaxed">
              {busyReason ?? "El ordenador está ocupado con otro objeto. Termina en el ordenador para continuar."}
            </p>
          </div>
          <button
            type="button"
            disabled
            className="mt-auto flex h-14 items-center justify-center gap-2 rounded-full bg-fog text-[15px] font-semibold text-ink-2"
          >
            <Clock className="size-5" aria-hidden /> Esperando a que el ordenador quede libre…
          </button>
        </>
      )}

      {phase === "completed" && (
        <>
          <Status
            icon={CircleCheck}
            text="Guardado en tu inventario. Si haces otra foto, el ordenador abrirá la revisión solo."
          />
          <button type="button" onClick={() => inputRef.current?.click()} className={PRIMARY_BUTTON}>
            <RotateCcw className="size-5" aria-hidden /> Hacer otra foto
          </button>
        </>
      )}
      {phase === "failed" && <Status icon={TriangleAlert} text="No se ha podido procesar la foto. Prueba otra vez." />}

      {(phase === "ready" || phase === "failed") && (
        <>
          <p className="text-base leading-relaxed text-ink-2">
            Haz una foto al objeto con buena luz. En el ordenador verás qué es, en qué estado está y cuánto vale.
          </p>
          <button type="button" onClick={() => inputRef.current?.click()} className={PRIMARY_BUTTON}>
            <Camera className="size-6" aria-hidden /> Hacer foto al objeto
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
    <p role="status" className="flex items-center gap-3 rounded-inner bg-fog p-4 text-[15px]">
      <Icon className={`size-6 shrink-0 text-ink-2 ${spin ? "animate-spin" : ""}`} aria-hidden /> {text}
    </p>
  );
}

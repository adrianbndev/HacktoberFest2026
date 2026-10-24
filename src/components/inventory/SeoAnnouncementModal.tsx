"use client";

import { useId, useRef, useState } from "react";
import { Check, ClipboardCopy, X } from "lucide-react";
import { useDialogScrollLock } from "@/components/ui/useDialogScrollLock";

interface SeoAnnouncementModalProps {
  itemName: string;
  seoTitle: string;
  seoDescription: string;
}

export function SeoAnnouncementModal({ itemName, seoTitle, seoDescription }: SeoAnnouncementModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [copy, setCopy] = useState<"idle" | "done" | "failed">("idle");
  useDialogScrollLock(dialogRef);

  async function copyAnnouncement() {
    try {
      await navigator.clipboard.writeText(`${seoTitle}\n\n${seoDescription}`);
      setCopy("done");
    } catch {
      setCopy("failed");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setCopy("idle");
          dialogRef.current?.showModal();
        }}
        className="flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-paper text-[15px] font-semibold transition-colors hover:bg-fog-2"
      >
        <ClipboardCopy className="size-4" aria-hidden /> Copiar anuncio
        <span className="sr-only"> de {itemName}</span>
      </button>

      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        className="m-auto w-[min(92vw,34rem)] overscroll-contain rounded-panel bg-paper p-6 text-ink backdrop:bg-black/55 backdrop:backdrop-blur-sm sm:p-7"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 id={titleId} className="text-lg font-semibold">Anuncio listo para publicar</h2>
            <p className="text-sm text-ink-2">{itemName}</p>
          </div>
          <form method="dialog">
            <button aria-label="Cerrar" className="grid size-9 place-items-center rounded-full transition-colors hover:bg-fog">
              <X className="size-5" aria-hidden />
            </button>
          </form>
        </div>
        <div className="rounded-inner bg-fog p-4">
          <p className="text-[13px] text-ink-2">Título</p>
          <p className="mt-0.5 font-semibold">{seoTitle}</p>
          <p className="mt-4 text-[13px] text-ink-2">Descripción</p>
          <p className="mt-0.5 whitespace-pre-line text-[15px] leading-relaxed">{seoDescription}</p>
        </div>
        <button
          type="button"
          onClick={copyAnnouncement}
          className="mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-full bg-accent text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          {copy === "done" ? <Check className="size-4" aria-hidden /> : <ClipboardCopy className="size-4" aria-hidden />}
          {copy === "done" ? "Copiado: pégalo en Wallapop" : "Copiar título y descripción"}
        </button>
        {copy === "failed" && (
          <p role="alert" className="mt-2 text-center text-sm text-rose-700">
            El navegador no permite copiar aquí: selecciona el texto y cópialo a mano.
          </p>
        )}
      </dialog>
    </>
  );
}

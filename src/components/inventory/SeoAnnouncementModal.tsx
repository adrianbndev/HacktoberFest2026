"use client";

import { useRef, useState } from "react";
import { Check, ClipboardCopy, X } from "lucide-react";

interface SeoAnnouncementModalProps {
  seoTitle: string;
  seoDescription: string;
}

export function SeoAnnouncementModal({ seoTitle, seoDescription }: SeoAnnouncementModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [copy, setCopy] = useState<"idle" | "done" | "failed">("idle");

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
        className="flex w-full items-center justify-center gap-2 rounded-2xl border border-zinc-200 py-2.5 text-sm font-medium transition hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
      >
        <ClipboardCopy className="size-4" aria-hidden /> Copiar anuncio SEO para Wallapop
      </button>

      <dialog
        ref={dialogRef}
        aria-labelledby="seo-title"
        className="m-auto w-[min(92vw,32rem)] rounded-3xl bg-white p-6 text-zinc-900 backdrop:bg-black/50 dark:bg-zinc-900 dark:text-zinc-100"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="seo-title" className="text-lg font-semibold">Anuncio listo para publicar</h2>
          <form method="dialog">
            <button aria-label="Cerrar" className="rounded-full p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800">
              <X className="size-5" aria-hidden />
            </button>
          </form>
        </div>
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Título</p>
        <p className="mb-4 mt-1 font-semibold">{seoTitle}</p>
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Descripción</p>
        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed">{seoDescription}</p>
        <button
          type="button"
          onClick={copyAnnouncement}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-zinc-900 py-3 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900"
        >
          {copy === "done" ? <Check className="size-4" aria-hidden /> : <ClipboardCopy className="size-4" aria-hidden />}
          {copy === "done" ? "¡Copiado!" : "Copiar título y descripción"}
        </button>
        {copy === "failed" && (
          <p role="alert" className="mt-2 text-center text-xs text-rose-600">
            El navegador no permite copiar aquí: selecciona el texto y cópialo a mano.
          </p>
        )}
      </dialog>
    </>
  );
}

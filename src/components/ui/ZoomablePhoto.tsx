"use client";

import { useRef, type ReactNode } from "react";
import { Maximize2, X } from "lucide-react";

interface ZoomablePhotoProps {
  src: string;
  alt: string;
  className: string;
  children?: ReactNode;
}

// Foto recortada que, al pulsarla, se abre entera (sin recortes) sobre fondo oscuro; Esc o clic la cierran.
export function ZoomablePhoto({ src, alt, className, children }: ZoomablePhotoProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button
        type="button"
        onClick={() => dialogRef.current?.showModal()}
        aria-label={`Ampliar: ${alt}`}
        className="group relative block w-full cursor-zoom-in"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- foto en data URL */}
        <img src={src} alt={alt} className={className} />
        <span className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-full bg-paper/90 px-3 py-1.5 text-[13px] font-semibold text-ink">
          <Maximize2 className="size-3.5" aria-hidden /> Ver foto completa
        </span>
      </button>
      {children}
      <dialog
        ref={dialogRef}
        onClick={() => dialogRef.current?.close()}
        aria-label={alt}
        className="m-auto max-h-none max-w-none overflow-visible bg-transparent p-0 backdrop:bg-black/85"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- foto en data URL */}
        <img src={src} alt={alt} className="max-h-[90dvh] max-w-[92vw] rounded-inner object-contain" />
        <button
          type="button"
          aria-label="Cerrar la foto"
          className="fixed right-5 top-5 grid size-11 place-items-center rounded-full bg-white text-black"
        >
          <X className="size-5" aria-hidden />
        </button>
      </dialog>
    </>
  );
}

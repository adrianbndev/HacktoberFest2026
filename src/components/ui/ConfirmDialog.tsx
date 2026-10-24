"use client";

import { useEffect, useId, useRef } from "react";
import { useDialogScrollLock } from "./useDialogScrollLock";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

// Confirmación antes de una acción que no se puede deshacer (eliminar, restaurar la demo).
export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);

  useDialogScrollLock(dialogRef, open);

  return (
    <dialog
      ref={dialogRef}
      onClose={onCancel}
      aria-labelledby={titleId}
      className="m-auto w-[min(92vw,26rem)] overscroll-contain rounded-panel bg-paper p-6 text-ink backdrop:bg-black/55 backdrop:backdrop-blur-sm"
    >
      <h2 id={titleId} className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{body}</p>
      <div className="mt-6 flex justify-end gap-2">
        <form method="dialog">
          <button className="h-11 rounded-full bg-fog px-5 text-[15px] font-semibold transition-colors hover:bg-fog-2">
            Cancelar
          </button>
        </form>
        <button
          type="button"
          onClick={onConfirm}
          className="h-11 rounded-full bg-rose-700 px-5 text-[15px] font-semibold text-white transition-colors hover:bg-rose-800"
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}

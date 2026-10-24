"use client";

import { useEffect, type RefObject } from "react";

function syncDocumentScrollLock() {
  const hasOpenDialog = document.querySelector("dialog[open]") !== null;
  const overflow = hasOpenDialog ? "hidden" : "";
  document.documentElement.style.overflow = overflow;
  document.body.style.overflow = overflow;
}

function canScrollVertically(target: EventTarget | null, dialog: HTMLDialogElement, deltaY: number): boolean {
  let node = target instanceof HTMLElement ? target : null;
  while (node && dialog.contains(node)) {
    if (node.scrollHeight > node.clientHeight) {
      const style = window.getComputedStyle(node);
      if (node === dialog || style.overflowY === "auto" || style.overflowY === "scroll") {
        if (deltaY < 0 && node.scrollTop > 0) return true;
        if (deltaY > 0 && node.scrollTop + node.clientHeight < node.scrollHeight - 1) return true;
      }
    }
    if (node === dialog) break;
    node = node.parentElement;
  }
  return false;
}

// Bloquea el scroll de la página principal mientras un <dialog> esté abierto.
export function useDialogScrollLock(dialogRef: RefObject<HTMLDialogElement | null>, open?: boolean) {
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    syncDocumentScrollLock();

    const observer = new MutationObserver(syncDocumentScrollLock);
    observer.observe(dialog, { attributes: true, attributeFilter: ["open"] });

    function handleWheel(event: WheelEvent) {
      if (!dialog || !dialog.open) return;
      const rect = dialog.getBoundingClientRect();
      const insideBox =
        event.clientX >= rect.left &&
        event.clientX <= rect.right &&
        event.clientY >= rect.top &&
        event.clientY <= rect.bottom;
      if (!insideBox || !canScrollVertically(event.target, dialog, event.deltaY)) {
        event.preventDefault();
      }
    }

    dialog.addEventListener("close", syncDocumentScrollLock);
    dialog.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      observer.disconnect();
      dialog.removeEventListener("close", syncDocumentScrollLock);
      dialog.removeEventListener("wheel", handleWheel);
      syncDocumentScrollLock();
    };
  }, [dialogRef, open]);
}

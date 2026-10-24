"use client";

import { Camera } from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardShell";
import { formatEur } from "./format";
import { InventoryItemCard } from "./InventoryItemCard";

export function InventoryView() {
  const { inventory, loadingInventory, openCapture } = useDashboard();
  const current = loadingInventory ? undefined : inventory ?? undefined;
  const items = current?.items;
  const soldCount = items?.filter((item) => item.status === "sold").length ?? 0;

  const captureButton = (
    <button
      type="button"
      onClick={openCapture}
      className="flex h-12 items-center gap-2.5 rounded-full bg-accent px-6 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover"
    >
      <Camera className="size-5" aria-hidden /> Tasar un objeto
    </button>
  );

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-semibold tracking-[-0.03em]">Mi inventario</h1>
          <p className="mt-1.5 text-ink-2" aria-live="polite">
            {current
              ? `${current.totals.itemCount} ${current.totals.itemCount === 1 ? "objeto" : "objetos"} · ${formatEur(current.totals.totalAvg)} de precio justo${soldCount ? ` · ${soldCount} vendido${soldCount === 1 ? "" : "s"}` : ""}`
              : "Cargando tu inventario…"}
          </p>
        </div>
        {captureButton}
      </div>

      <section aria-label="Tus objetos" aria-busy={!items}>
        {!items ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((key) => (
              <div key={key} className="overflow-hidden rounded-panel bg-fog">
                <div className="aspect-[4/3] animate-pulse bg-fog-2" />
                <div className="flex flex-col gap-3 p-5">
                  <span className="h-5 w-3/4 animate-pulse rounded-full bg-fog-2" />
                  <span className="h-4 w-1/2 animate-pulse rounded-full bg-fog-2" />
                  <span className="mt-4 h-9 w-1/3 animate-pulse rounded-full bg-fog-2" />
                  <span className="h-1.5 animate-pulse rounded-full bg-fog-2" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-start gap-4 rounded-panel bg-fog p-8">
            <h2 className="text-xl font-semibold">Tu inventario está vacío</h2>
            <p className="max-w-md text-ink-2">
              Haz una foto de algo que tengas en casa y en segundos sabrás su estado y cuánto vale.
            </p>
            {captureButton}
          </div>
        ) : (
          <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <InventoryItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}

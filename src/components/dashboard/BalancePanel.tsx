"use client";

import Link from "next/link";
import { ArrowRight, Camera, ChevronDown } from "lucide-react";
import type { InventoryTotals } from "@/types/sdd";
import { RangeRuler } from "@/components/inventory/PriceTrioDisplay";
import { formatEur } from "@/components/inventory/format";
import { useRollingNumber } from "./useRollingNumber";

interface BalancePanelProps {
  totals?: InventoryTotals;
  onCapture: () => void;
}

export function BalancePanel({ totals, onCapture }: BalancePanelProps) {
  const rolling = useRollingNumber(totals?.totalAvg);
  const count = totals?.itemCount ?? 0;

  return (
    <section aria-labelledby="balance-title" className="flex h-full flex-col gap-8 rounded-panel bg-accent p-6 text-white sm:p-8">
      <div>
        <h1 id="balance-title" className="text-base font-medium text-on-accent-2">Tu patrimonio</h1>
        {totals && rolling !== undefined ? (
          <>
            <p aria-hidden className="mt-2 font-display text-[clamp(3.5rem,8vw,6rem)] font-semibold leading-none tracking-[-0.04em] tabular-nums">
              {formatEur(rolling)}
            </p>
            <p className="sr-only" aria-live="polite">{formatEur(totals.totalAvg)}</p>
            <p className="mt-4 text-on-accent-2">
              Precio justo de {count === 1 ? "tu objeto" : `tus ${count} objetos`}, comparado con Wallapop, Vinted,
              Milanuncios y eBay.
            </p>
          </>
        ) : (
          <div aria-busy className="mt-3 flex flex-col gap-4">
            <span className="block h-[clamp(3.5rem,8vw,6rem)] w-3/5 animate-pulse rounded-inner bg-white/15" />
            <span className="block h-5 w-4/5 animate-pulse rounded-full bg-white/15" />
          </div>
        )}
      </div>

      {totals && totals.itemCount > 0 && (
        <RangeRuler priceMin={totals.totalMin} priceAvg={totals.totalAvg} priceMax={totals.totalMax} onAccent />
      )}

      {/* En escritorio el bloque se estira a la altura de la columna derecha: las acciones van al fondo. */}
      <div className="mt-auto flex flex-col gap-8">
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onCapture}
            className="flex h-12 items-center gap-2.5 rounded-full bg-white px-6 text-[15px] font-semibold text-accent transition-transform hover:scale-[1.02] focus-visible:outline-white active:scale-[0.98]"
          >
            <Camera className="size-5" aria-hidden /> Tasar un objeto
          </button>
          <Link
            href="/inventario"
            className="flex h-12 items-center gap-2 rounded-full bg-white/12 px-6 text-[15px] font-semibold ring-1 ring-white/35 transition-colors ring-inset hover:bg-white/20 focus-visible:outline-white"
          >
            Mi inventario <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>

        <details className="group -mt-2 border-t border-white/20 pt-4">
          <summary className="flex items-center gap-1.5 rounded-sm text-[15px] font-medium text-on-accent-2 hover:text-white focus-visible:outline-white">
            ¿Cómo se calcula?
            <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <dl className="mt-3 grid gap-2 text-[15px] leading-relaxed text-on-accent-2">
            <div>
              <dt className="inline font-semibold text-white">Venta rápida: </dt>
              <dd className="inline">lo que te darían si lo vendes hoy.</dd>
            </div>
            <div>
              <dt className="inline font-semibold text-white">Precio justo: </dt>
              <dd className="inline">su valor de mercado según el estado que detecta la IA en la foto.</dd>
            </div>
            <div>
              <dt className="inline font-semibold text-white">Máximo: </dt>
              <dd className="inline">lo que puedes pedir si está impecable y no tienes prisa.</dd>
            </div>
          </dl>
        </details>
      </div>
    </section>
  );
}

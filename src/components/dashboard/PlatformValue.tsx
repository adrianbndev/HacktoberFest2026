"use client";

import type { InventoryItem } from "@/types/sdd";
import { PLATFORM_LABEL, formatEur } from "@/components/inventory/format";
import { ValuatingAggregateNote } from "@/components/inventory/ValuatingPriceSkeleton";
import { useDashboard } from "./DashboardShell";
import { platformTotals, settledItems } from "./inventory-aggregates";

// Gráfico de énfasis: la plataforma donde más vale en el acento, el resto en gris; cada valor va escrito.
export function PlatformValue({ items }: { items?: InventoryItem[] }) {
  const { pendingValuations } = useDashboard();
  const totals = items ? platformTotals(settledItems(items, pendingValuations)) : [];
  const pendingCount = Object.keys(pendingValuations).length;
  if (totals.length < 2) return null;
  const max = totals[0].value;
  const mean = totals.reduce((sum, { value }) => sum + value, 0) / totals.length;
  const percentAbove = (value: number) => Math.round((value / mean - 1) * 100);
  const best = totals[0];

  return (
    <section aria-labelledby="platform-title" className="h-full rounded-panel bg-fog p-5 sm:p-7">
      <h2 id="platform-title" className="text-xl font-semibold">Dónde vale más tu inventario</h2>
      <p className="mt-1.5 max-w-prose text-ink-2">
        En <span className="font-semibold text-ink">{PLATFORM_LABEL[best.platform]}</span> suma{" "}
        <span className="font-semibold tabular-nums text-ink">{formatEur(best.value)}</span>, un{" "}
        {percentAbove(best.value)} % más que la media de las {totals.length} plataformas.
      </p>
      <ul className="mt-6 flex flex-col gap-4">
        {totals.map(({ platform, value }, index) => {
          const delta = percentAbove(value);
          return (
            <li
              key={platform}
              title={`${PLATFORM_LABEL[platform]}: ${formatEur(value)} · ${delta > 0 ? "+" : ""}${delta} % frente a la media`}
              className="grid grid-cols-[6.5rem_minmax(0,1fr)_4.5rem] items-center gap-4"
            >
              <span className="text-[15px] font-medium">{PLATFORM_LABEL[platform]}</span>
              <span aria-hidden className="h-2.5 rounded-full bg-paper">
                <span
                  className={`block h-full rounded-full ${index === 0 ? "bg-accent" : "bg-ink/25"}`}
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </span>
              <span className="text-right font-semibold tabular-nums">{formatEur(value)}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-6 text-[13px] text-ink-2">Según los precios de referencia de cada objeto en cada plataforma.</p>
      {pendingCount > 0 && (
        <div className="mt-3 border-t border-line pt-1">
          <ValuatingAggregateNote label={`Tasando ${pendingCount === 1 ? "un objeto" : `${pendingCount} objetos`}…`} />
        </div>
      )}
    </section>
  );
}

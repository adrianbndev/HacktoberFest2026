"use client";

import { createElement } from "react";
import { CircleCheck, Clock, House, Store, type LucideIcon } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { STATUS_LABEL, formatEur } from "@/components/inventory/format";
import { ValuatingAggregateNote } from "@/components/inventory/ValuatingPriceSkeleton";
import { useDashboard } from "./DashboardShell";
import { settledItems, statusTotals } from "./inventory-aggregates";

const STATUS_ICONS: Record<InventoryItem["status"], LucideIcon> = {
  in_stock: House,
  listed: Store,
  reserved: Clock,
  sold: CircleCheck,
};

// Cuántos objetos hay en cada estado y su precio justo sumado. Las tasaciones en curso no cuentan.
export function InventoryByStatus({ items }: { items?: InventoryItem[] }) {
  const { pendingValuations } = useDashboard();
  if (!items || items.length === 0) return null;
  const settled = settledItems(items, pendingValuations);
  const rows = statusTotals(settled).filter(
    ({ status, count }) => count > 0 || (settled.length > 0 && status !== "reserved"),
  );
  const pendingCount = Object.keys(pendingValuations).length;

  return (
    <section aria-labelledby="by-status-title" className="h-full rounded-panel bg-fog p-3 sm:p-4">
      <h2 id="by-status-title" className="px-3 pt-2 text-xl font-semibold">Tu inventario por estado</h2>
      <ul className="mt-2">
        {rows.map(({ status, count, value }) => (
          <li key={status} className="flex items-center gap-3 px-3 py-2.5">
            <span className="grid size-11 shrink-0 place-items-center rounded-full bg-paper">
              {createElement(STATUS_ICONS[status], { className: "size-5", "aria-hidden": true })}
            </span>
            <span className="flex-1 font-semibold">{STATUS_LABEL[status]}</span>
            <span className="text-ink-2">
              {count} {count === 1 ? "objeto" : "objetos"}
            </span>
            <span className="w-20 text-right font-semibold tabular-nums">{formatEur(value)}</span>
          </li>
        ))}
      </ul>
      {pendingCount > 0 && (
        <div className="mt-2 border-t border-line pt-2">
          <ValuatingAggregateNote label={`Tasando ${pendingCount === 1 ? "un objeto" : `${pendingCount} objetos`}…`} />
        </div>
      )}
    </section>
  );
}

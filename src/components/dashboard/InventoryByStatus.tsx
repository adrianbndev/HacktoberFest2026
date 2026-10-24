"use client";

import { createElement } from "react";
import { CircleCheck, Clock, House, Store, type LucideIcon } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { STATUS_LABEL, formatEur } from "@/components/inventory/format";

const STATUSES: { status: InventoryItem["status"]; icon: LucideIcon }[] = [
  { status: "in_stock", icon: House },
  { status: "listed", icon: Store },
  { status: "reserved", icon: Clock },
  { status: "sold", icon: CircleCheck },
];

// Cuántos objetos hay en cada estado y su precio justo sumado (Reservado solo aparece si hay alguno).
export function InventoryByStatus({ items }: { items?: InventoryItem[] }) {
  if (!items || items.length === 0) return null;
  const rows = STATUSES.map(({ status, icon }) => {
    const group = items.filter((item) => item.status === status);
    return { status, icon, count: group.length, value: group.reduce((sum, item) => sum + item.priceAvg, 0) };
  }).filter(({ status, count }) => status !== "reserved" || count > 0);

  return (
    <section aria-labelledby="by-status-title" className="rounded-panel bg-fog p-3 sm:p-4">
      <h2 id="by-status-title" className="px-3 pt-2 text-xl font-semibold">Tu inventario por estado</h2>
      <ul className="mt-2">
        {rows.map(({ status, icon, count, value }) => (
          <li key={status} className="flex items-center gap-3 px-3 py-2.5">
            <span className="grid size-11 shrink-0 place-items-center rounded-full bg-paper">
              {createElement(icon, { className: "size-5", "aria-hidden": true })}
            </span>
            <span className="flex-1 font-semibold">{STATUS_LABEL[status]}</span>
            <span className="text-ink-2">
              {count} {count === 1 ? "objeto" : "objetos"}
            </span>
            <span className="w-20 text-right font-semibold tabular-nums">{formatEur(value)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

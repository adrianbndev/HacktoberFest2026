"use client";

import { createElement } from "react";
import Link from "next/link";
import { Camera, Plus } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { STATUS_LABEL, categoryIcon, formatDayLabel, formatEur, formatTime } from "@/components/inventory/format";

const RECENT_COUNT = 5;

interface RecentValuationsProps {
  items?: InventoryItem[];
  lastAddedId: string | null;
  onCapture: () => void;
}

// Últimas tasaciones como movimientos de una cuenta: sin fotos, agrupadas por día.
export function RecentValuations({ items, lastAddedId, onCapture }: RecentValuationsProps) {
  const recent = items?.slice(0, RECENT_COUNT);
  const groups = new Map<string, InventoryItem[]>();
  for (const item of recent ?? []) {
    const day = formatDayLabel(item.createdAt);
    groups.set(day, [...(groups.get(day) ?? []), item]);
  }

  return (
    <section aria-labelledby="recent-title" aria-busy={!items} className="flex h-full flex-col rounded-panel bg-fog p-3 sm:p-4">
      <div className="flex items-baseline justify-between px-3 pb-1 pt-2">
        <h2 id="recent-title" className="text-xl font-semibold">Tasaciones recientes</h2>
        {items && items.length > 0 && (
          <Link href="/inventario" className="text-[15px] font-semibold text-accent hover:underline">
            Ver todo
          </Link>
        )}
      </div>

      {!recent ? (
        <ul className="mt-3 flex flex-col gap-1">
          {[0, 1, 2].map((key) => (
            <li key={key} className="flex items-center gap-3 px-3 py-3">
              <span className="size-11 animate-pulse rounded-full bg-fog-2" />
              <span className="h-4 flex-1 animate-pulse rounded-full bg-fog-2" />
              <span className="h-4 w-16 animate-pulse rounded-full bg-fog-2" />
            </li>
          ))}
        </ul>
      ) : recent.length === 0 ? (
        <div className="flex flex-col items-start gap-4 px-3 py-8">
          <p className="max-w-xs text-ink-2">Aún no has tasado nada. Haz una foto con el móvil y aparecerá aquí.</p>
          <button
            type="button"
            onClick={onCapture}
            className="flex h-11 items-center gap-2 rounded-full bg-accent px-5 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            <Camera className="size-4.5" aria-hidden /> Tasar un objeto
          </button>
        </div>
      ) : (
        <>
          {[...groups].map(([day, dayItems]) => (
            <div key={day} className="mt-3">
              <h3 className="px-3 pb-1 text-sm font-medium text-ink-2">{day}</h3>
              <ul>
                {dayItems.map((item) => (
                  <RecentRow key={item.id} item={item} isNew={item.id === lastAddedId} />
                ))}
              </ul>
            </div>
          ))}
          <button
            type="button"
            onClick={onCapture}
            className="mt-auto flex items-center gap-3 rounded-inner px-3 py-3 text-left font-semibold text-accent transition-colors hover:bg-paper"
          >
            <span className="grid size-11 shrink-0 place-items-center rounded-full border-2 border-dashed border-accent/35">
              <Plus className="size-5" aria-hidden />
            </span>
            Tasar otro objeto
          </button>
        </>
      )}
    </section>
  );
}

function RecentRow({ item, isNew }: { item: InventoryItem; isNew: boolean }) {
  return (
    <li>
      <Link
        href={`/inventario#${item.id}`}
        className={`flex items-center gap-3 rounded-inner px-3 py-3 transition-colors hover:bg-paper ${isNew ? "animate-row-arrive" : ""}`}
      >
        <span className="grid size-11 shrink-0 place-items-center rounded-full bg-paper text-ink">
          {createElement(categoryIcon(item.category), { className: "size-5", "aria-hidden": true })}
        </span>
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 font-semibold leading-snug">{item.name}</span>
          <span className="block truncate text-sm text-ink-2">
            {formatTime(item.createdAt)} · {item.conditionLabel} · {STATUS_LABEL[item.status]}
          </span>
        </span>
        <span className="shrink-0 text-right">
          <span className={`block font-semibold tabular-nums ${isNew ? "text-accent" : ""}`}>
            {isNew && "+"}
            {formatEur(item.priceAvg)}
          </span>
          <span className="hidden text-sm tabular-nums text-ink-2 sm:block">
            {formatEur(item.priceMin)}–{formatEur(item.priceMax)}
          </span>
        </span>
      </Link>
    </li>
  );
}

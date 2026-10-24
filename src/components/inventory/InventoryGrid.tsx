import { PackageOpen } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { InventoryItemCard } from "./InventoryItemCard";

interface InventoryGridProps {
  items?: InventoryItem[];
  loading: boolean;
}

export function InventoryGrid({ items, loading }: InventoryGridProps) {
  return (
    <section aria-labelledby="inventory-title" aria-busy={loading}>
      <div className="mb-4 flex items-baseline justify-between">
        <h2 id="inventory-title" className="text-xl font-semibold">Mi Inventario</h2>
        {items && <span className="text-sm text-zinc-500 dark:text-zinc-400">{items.length} productos</span>}
      </div>

      {!items ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((key) => (
            <div key={key} className="h-[34rem] animate-pulse rounded-3xl bg-zinc-200 dark:bg-zinc-900" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-zinc-300 py-16 text-center dark:border-zinc-700">
          <PackageOpen className="size-10 text-zinc-400" aria-hidden />
          <p className="font-medium">Todavía no hay productos en tu inventario</p>
        </div>
      ) : (
        <div className={`grid gap-4 transition-opacity sm:grid-cols-2 lg:grid-cols-3 ${loading ? "opacity-50" : ""}`}>
          {items.map((item) => (
            <InventoryItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

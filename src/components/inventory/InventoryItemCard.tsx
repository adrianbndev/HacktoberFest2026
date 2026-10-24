import { ExternalLink } from "lucide-react";
import type { InventoryItem, MarketPlatform } from "@/types/sdd";
import { formatEur } from "./format";
import { HealthScoreBadge } from "./HealthScoreBadge";
import { PriceTrioDisplay } from "./PriceTrioDisplay";
import { SeoAnnouncementModal } from "./SeoAnnouncementModal";

const STATUS_LABEL: Record<InventoryItem["status"], string> = {
  in_stock: "En casa",
  listed: "Publicado",
  reserved: "Reservado",
  sold: "Vendido",
};

const PLATFORM_LABEL: Record<MarketPlatform, string> = {
  wallapop: "Wallapop",
  vinted: "Vinted",
  milanuncios: "Milanuncios",
  ebay: "eBay",
};

export function InventoryItemCard({ item }: { item: InventoryItem }) {
  return (
    <article className="flex flex-col overflow-hidden rounded-3xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="relative aspect-[4/3] bg-zinc-100 dark:bg-zinc-800">
        {/* eslint-disable-next-line @next/next/no-img-element -- fotos en data URL desde el móvil */}
        <img src={item.photoUrl} alt={item.name} className="size-full object-cover" />
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2.5 py-1 text-xs font-medium text-zinc-900 backdrop-blur">
          {STATUS_LABEL[item.status]}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-5 p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{item.category}</p>
          <h3 className="mt-1 text-base font-semibold leading-snug">{item.name}</h3>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {item.brand} · {item.model}
          </p>
        </div>

        <HealthScoreBadge score={item.conditionScore} label={item.conditionLabel} reasoning={item.conditionReasoning} />
        {item.details && (
          <p className="whitespace-pre-line rounded-2xl bg-zinc-100 p-3 text-xs leading-relaxed text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
            {item.details}
          </p>
        )}
        <PriceTrioDisplay priceMin={item.priceMin} priceAvg={item.priceAvg} priceMax={item.priceMax} />

        {item.comparableListings.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-zinc-500 dark:text-zinc-400">Comparables en el mercado</p>
            <ul className="flex flex-wrap gap-1.5">
              {item.comparableListings.map((listing) => (
                <li key={listing.platform}>
                  <a
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs transition hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                  >
                    {PLATFORM_LABEL[listing.platform]} {formatEur(listing.price)}
                    <ExternalLink className="size-3" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-auto">
          <SeoAnnouncementModal seoTitle={item.seoTitle} seoDescription={item.seoDescription} />
        </div>
      </div>
    </article>
  );
}

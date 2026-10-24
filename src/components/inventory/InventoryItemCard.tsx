import { createElement } from "react";
import { ChevronDown, ExternalLink } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { PLATFORM_LABEL, STATUS_LABEL, categoryIcon, formatEur, formatPlatforms, formatShortDay } from "./format";
import { DEMO_PHOTO_CREDITS } from "./demo-photo-credits";
import { ConditionChip } from "./HealthScoreBadge";
import { ItemActions } from "./ItemActions";
import { PriceTrioDisplay } from "./PriceTrioDisplay";
import { SeoAnnouncementModal } from "./SeoAnnouncementModal";

export function InventoryItemCard({ item }: { item: InventoryItem }) {
  const sold = item.status === "sold";
  // Los productos de demo (seed_data.py) traen un dibujo SVG, no una foto: se muestran como ejemplo.
  const examplePhoto = item.photoUrl.startsWith("data:image/svg+xml");
  const credit = DEMO_PHOTO_CREDITS[item.id];
  return (
    <article
      id={item.id}
      className="flex scroll-mt-6 flex-col overflow-hidden rounded-panel bg-fog target:ring-2 target:ring-accent target:ring-offset-2"
    >
      <div className="relative aspect-[4/3] bg-fog-2">
        {examplePhoto ? (
          <div className="absolute inset-0 grid place-items-center text-ink-2">
            {createElement(categoryIcon(item.category), { className: "size-14", strokeWidth: 1.25, "aria-hidden": true })}
            <span className="absolute bottom-3 right-3 rounded-full bg-paper/90 px-2.5 py-1 text-[13px] font-medium">
              Foto de ejemplo
            </span>
          </div>
        ) : (
          /* eslint-disable-next-line @next/next/no-img-element -- fotos en data URL desde el móvil */
          <img
            src={item.photoUrl}
            alt={item.name}
            className={`absolute inset-0 size-full object-cover ${sold ? "grayscale" : ""}`}
          />
        )}
        {credit && !examplePhoto && (
          <a
            href={credit.source}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute bottom-2 right-2 rounded-full bg-paper/85 px-2 py-0.5 text-[12px] text-ink-2 transition-colors hover:text-ink"
          >
            Foto: {credit.author} · {credit.license}
            <span className="sr-only"> (se abre en una pestaña nueva)</span>
          </a>
        )}
        <span
          className={`absolute left-3 top-3 rounded-full px-3 py-1 text-[13px] font-semibold shadow-[0_2px_8px_rgb(16_17_20/0.15)] ${
            sold ? "bg-ink text-white" : "bg-paper text-ink"
          }`}
        >
          {STATUS_LABEL[item.status]}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-5 p-5">
        <div>
          <h3 className="text-[17px] font-semibold leading-snug">{item.name}</h3>
          <p className="mt-0.5 truncate text-sm text-ink-2">
            {item.brand} · {item.model}
          </p>
          <div className="mt-3">
            <ConditionChip label={item.conditionLabel} />
          </div>
        </div>

        <PriceTrioDisplay priceMin={item.priceMin} priceAvg={item.priceAvg} priceMax={item.priceMax} />

        <details className="group border-t border-line pt-4">
          <summary className="flex items-center justify-between gap-2 text-[15px] font-semibold">
            Detalles de la tasación
            <ChevronDown className="size-4 text-ink-2 transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <div className="mt-3 flex flex-col gap-4 text-sm leading-relaxed">
            <p className="text-ink-2">
              Tasado el {formatShortDay(item.lastUpdatedAt)} con precios de referencia de {formatPlatforms(item)}.
            </p>
            <div>
              <p className="font-semibold">Estado: {item.conditionScore}/100</p>
              <p className="text-ink-2">{item.conditionReasoning}</p>
            </div>
            {item.details && (
              <div>
                <p className="font-semibold">Tus notas</p>
                <p className="whitespace-pre-line text-ink-2">{item.details}</p>
              </div>
            )}
            {item.comparableListings.length > 0 && (
              <div>
                <p className="font-semibold">Referencia por plataforma</p>
                <ul className="mt-1">
                  {item.comparableListings.map((listing) => (
                    <li key={listing.platform} className="flex items-center justify-between gap-3 py-1">
                      <span className="text-ink-2">
                        {PLATFORM_LABEL[listing.platform]} · <span className="tabular-nums">{formatEur(listing.price)}</span>
                      </span>
                      <a
                        href={listing.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-semibold text-accent hover:underline"
                      >
                        Buscar <ExternalLink className="size-3.5" aria-hidden />
                        <span className="sr-only">
                          {item.name} en {PLATFORM_LABEL[listing.platform]} (se abre en una pestaña nueva)
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>

        <div className="mt-auto flex gap-2">
          <SeoAnnouncementModal itemName={item.name} seoTitle={item.seoTitle} seoDescription={item.seoDescription} />
          <ItemActions item={item} />
        </div>
      </div>
    </article>
  );
}

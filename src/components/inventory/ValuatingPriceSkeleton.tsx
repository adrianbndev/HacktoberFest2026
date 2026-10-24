"use client";

import { Check, Clock, Loader2, TriangleAlert } from "lucide-react";
import { MARKET_ANALYSIS_SOURCES } from "@/components/mobile-sync/vision-to-market";
import type { MarketSourceResult } from "@/types/market-analysis";
import { PLATFORM_LABEL } from "./format";

export interface ValuatingPriceSkeletonProps {
  sources?: MarketSourceResult[];
}

export function ValuatingPriceSkeleton({ sources = [] }: ValuatingPriceSkeletonProps) {
  const byPlatform = new Map(sources.map((s) => [s.source, s]));

  return (
    <div role="status" aria-live="polite" aria-busy="true" className="flex flex-col gap-3.5">
      <div className="flex items-center gap-2 rounded-inner bg-paper px-3 py-2 text-[13px] font-semibold text-accent ring-1 ring-line">
        <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
        <span>Buscando precios para comparar…</span>
      </div>

      <div>
        <span className="block text-[13px] text-ink-2">Precio justo</span>
        <span className="mt-1.5 block h-8 w-28 animate-pulse rounded-inner bg-fog-2" />
      </div>

      <div>
        <div aria-hidden className="h-1.5 w-full animate-pulse rounded-full bg-fog-2" />
        <dl className="mt-3 flex justify-between gap-4">
          <div>
            <dt className="text-[13px] text-ink-2">Venta rápida</dt>
            <dd className="mt-1">
              <span className="block h-5 w-16 animate-pulse rounded-full bg-fog-2" />
            </dd>
          </div>
          <div className="text-right">
            <dt className="text-[13px] text-ink-2">Máximo</dt>
            <dd className="mt-1 flex justify-end">
              <span className="block h-5 w-16 animate-pulse rounded-full bg-fog-2" />
            </dd>
          </div>
        </dl>
      </div>

      <ul className="flex flex-wrap gap-1.5 pt-0.5">
        {MARKET_ANALYSIS_SOURCES.map((platform) => {
          const result = byPlatform.get(platform);
          const ok = result?.status === "ok";
          const failed = result && result.status !== "ok";
          return (
            <li
              key={platform}
              className="flex items-center gap-1.5 rounded-full bg-paper px-2.5 py-1 text-[12px] font-medium text-ink-2 ring-1 ring-line"
            >
              {!result ? (
                <Loader2 className="size-3 animate-spin text-accent" aria-hidden />
              ) : ok ? (
                <Check className="size-3 text-accent" aria-hidden />
              ) : result.status === "timeout" ? (
                <Clock className="size-3 text-amber-600 dark:text-amber-400" aria-hidden />
              ) : (
                <TriangleAlert className="size-3 text-amber-600 dark:text-amber-400" aria-hidden />
              )}
              <span>{PLATFORM_LABEL[platform]}</span>
              {ok && result.sampleSize > 0 && (
                <span className="tabular-nums text-accent">· {result.sampleSize}</span>
              )}
              {failed && <span className="text-amber-700 dark:text-amber-400">· {result.status === "blocked" ? "bloq." : "sin datos"}</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ValuatingPlatformRefsSkeleton() {
  return (
    <div aria-busy="true">
      <p className="font-semibold">Referencia por plataforma</p>
      <ul className="mt-1.5 flex flex-col gap-2">
        {MARKET_ANALYSIS_SOURCES.map((platform) => (
          <li key={platform} className="flex items-center justify-between gap-3 py-1">
            <span className="flex items-center gap-2 text-ink-2">
              <span>{PLATFORM_LABEL[platform]}</span>
              <span className="inline-block h-4 w-14 animate-pulse rounded-full bg-fog-2" />
            </span>
            <span className="inline-block h-4 w-12 animate-pulse rounded-full bg-fog-2" />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ValuatingAggregateNote({ label = "Tasando un objeto…" }: { label?: string }) {
  return (
    <p role="status" className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-accent">
      <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
      {label}
    </p>
  );
}

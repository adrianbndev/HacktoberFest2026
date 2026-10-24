"use client";

import { Ban, Check, CircleDashed, CircleMinus, Clock, Loader2, RefreshCw, ShieldAlert, Sparkles, TriangleAlert } from "lucide-react";
import { PriceTrioDisplay } from "@/components/inventory/PriceTrioDisplay";
import { PLATFORM_LABEL, formatEur } from "@/components/inventory/format";
import type { MarketAnalysisRecommendation, MarketSourceResult } from "@/types/market-analysis";
import { buildMarketRows, type MarketRowStatus } from "./market-rows";

export interface MarketProgressProps {
  sources: MarketSourceResult[];
  recommendation?: MarketAnalysisRecommendation | null;
  warnings?: string[];
  error?: string | null;
  /** Set in the `done` step to replace the live progress with the final prices. */
  prices?: { priceMin: number; priceAvg: number; priceMax: number } | null;
  complete?: boolean;
  onRetry?: () => void;
}

const STATUS_TEXT: Record<MarketRowStatus, string> = {
  pending: "Pendiente",
  not_run: "Sin datos",
  ok: "OK",
  blocked: "Bloqueada",
  timeout: "Sin respuesta",
  no_listings: "Sin anuncios",
  error: "Error",
};

const STATUS_CLASS: Record<MarketRowStatus, string> = {
  pending: "text-ink-2",
  not_run: "text-ink-2",
  ok: "text-accent",
  blocked: "text-amber-700 dark:text-amber-400",
  timeout: "text-amber-700 dark:text-amber-400",
  no_listings: "text-ink-2",
  error: "text-rose-700 dark:text-rose-400",
};

// Códigos del backend que no deben llegar crudos al usuario; el resto (detalle en español) se muestra tal cual.
const ERROR_TEXT: Record<string, string> = {
  browser_unavailable:
    "El navegador que consulta los mercados no está disponible. Comprueba que el servicio market-browser esté levantado.",
  analysis_disabled: "El análisis profundo está desactivado en el backend.",
  analysis_failed: "El análisis falló por un error inesperado. Vuelve a intentarlo en unos segundos.",
  stream_unavailable: "El servidor no pudo abrir el progreso del análisis. Vuelve a intentarlo.",
  stream_ended_without_done: "El análisis se cortó antes de terminar. Vuelve a intentarlo.",
};

function StatusIcon({ status }: { status: MarketRowStatus }) {
  if (status === "pending") return <Loader2 className="size-4 animate-spin" aria-hidden />;
  if (status === "not_run") return <CircleDashed className="size-4" aria-hidden />;
  if (status === "ok") return <Check className="size-4" aria-hidden />;
  if (status === "timeout") return <Clock className="size-4" aria-hidden />;
  if (status === "no_listings") return <CircleMinus className="size-4" aria-hidden />;
  if (status === "error") return <TriangleAlert className="size-4" aria-hidden />;
  return <Ban className="size-4" aria-hidden />;
}

function errorMessage(detail: string): string {
  return ERROR_TEXT[detail] ?? detail;
}

export function MarketProgress({
  sources,
  recommendation,
  warnings = [],
  error,
  prices,
  complete = false,
  onRetry,
}: MarketProgressProps) {
  const rows = buildMarketRows(sources, Boolean(error));
  const usable = rows.filter((row) => row.status === "ok").length;
  const settled = rows.filter((row) => row.status !== "pending").length;
  const degraded = rows.some(
    (row) =>
      row.status === "blocked" ||
      row.status === "timeout" ||
      row.status === "no_listings" ||
      row.status === "not_run" ||
      row.status === "error",
  );
  const heading = error
    ? "Análisis de mercado"
    : complete
      ? "Precios reales de 3 mercados"
      : "Comparando precios en 3 mercados…";

  return (
    <section aria-live="polite" className="flex flex-col gap-4">
      <div>
        <p className="flex items-center gap-2 text-[15px] font-semibold">
          {!complete && !error ? (
            <Loader2 className="size-4.5 shrink-0 animate-spin text-accent" aria-hidden />
          ) : (
            <Sparkles className="size-4.5 shrink-0 text-accent" aria-hidden />
          )}
          {heading}
        </p>
        <ul className="mt-3 flex flex-col gap-1.5">
          {rows.map((row) => (
            <li key={row.source} className="flex items-center justify-between gap-3 rounded-inner bg-fog px-3.5 py-2.5">
              <span className="text-sm font-medium">{PLATFORM_LABEL[row.source]}</span>
              <span className={`flex items-center gap-1.5 text-sm tabular-nums ${STATUS_CLASS[row.status]}`}>
                <StatusIcon status={row.status} />
                {STATUS_TEXT[row.status]}
                {row.status === "ok" && row.sampleSize > 0 ? ` · ${row.sampleSize} anuncios` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {degraded && usable > 0 && (
        <p className="rounded-inner bg-amber-50 px-3.5 py-2.5 text-sm leading-relaxed text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
          Resultado parcial: {usable} de {settled} fuentes consultadas devolvieron anuncios. Los precios se calculan
          solo con datos reales de las fuentes disponibles.
        </p>
      )}

      {complete && prices && <PriceTrioDisplay {...prices} />}

      {complete && recommendation && (
        <div className="rounded-panel bg-fog p-4">
          <p className="flex items-center gap-2 text-[15px] font-semibold">
            <Sparkles className="size-4.5 text-accent" aria-hidden /> Recomendación de venta
          </p>
          <p className="mt-2 text-sm leading-relaxed text-ink-2">{recommendation.summary}</p>
          <p className="mt-3">
            <span className="block text-[13px] text-ink-2">Precio sugerido</span>
            <span className="font-display text-[1.75rem] font-semibold leading-tight tracking-[-0.03em] tabular-nums">
              {formatEur(recommendation.suggestedPrice)}
            </span>
          </p>
          {recommendation.bullets.length > 0 && (
            <ul className="mt-3 flex list-disc flex-col gap-1.5 pl-5 text-sm leading-relaxed text-ink-2">
              {recommendation.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          )}
          {recommendation.risks.length > 0 && (
            <div className="mt-3 rounded-inner bg-paper p-3">
              <p className="flex items-center gap-1.5 text-[13px] font-semibold text-ink-2">
                <ShieldAlert className="size-4 text-amber-700 dark:text-amber-400" aria-hidden /> A tener en cuenta
              </p>
              <ul className="mt-1.5 flex list-disc flex-col gap-1 pl-5 text-sm leading-relaxed text-ink-2">
                {recommendation.risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <details className="rounded-inner bg-fog px-3.5 py-2.5 text-sm text-ink-2">
          <summary className="cursor-pointer font-medium">Avisos del análisis ({warnings.length})</summary>
          <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 leading-relaxed">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      )}

      {error && (
        <div className="flex flex-col gap-3">
          <p
            role="alert"
            className="flex items-start gap-2.5 rounded-inner bg-rose-50 p-4 text-sm leading-relaxed text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
          >
            <TriangleAlert className="mt-0.5 size-5 shrink-0" aria-hidden />
            <span>
              <span className="block font-semibold">No hemos podido completar la tasación.</span>
              {errorMessage(error)}
            </span>
          </p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="flex h-11 items-center justify-center gap-2 rounded-full bg-accent px-5 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              <RefreshCw className="size-4" aria-hidden /> Reintentar análisis
            </button>
          )}
        </div>
      )}
    </section>
  );
}

import { MapPin, Target, TrendingDown, TrendingUp } from "lucide-react";
import type { InventoryTotals, UserProfile } from "@/types/sdd";
import { formatEur } from "@/components/inventory/format";

interface PatrimonyBentoHeaderProps {
  profile?: UserProfile;
  totals?: InventoryTotals;
}

const card = "rounded-3xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900";

function Amount({ value, className }: { value?: number; className: string }) {
  if (value === undefined) return <span className="block h-9 w-32 animate-pulse rounded-lg bg-zinc-200 dark:bg-zinc-800" />;
  return <span className={`block font-semibold tabular-nums tracking-tight ${className}`}>{formatEur(value)}</span>;
}

export function PatrimonyBentoHeader({ profile, totals }: PatrimonyBentoHeaderProps) {
  return (
    <section aria-label="Valoración de tu inventario" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className={`${card} flex flex-col justify-between gap-6 sm:col-span-2 lg:row-span-2`}>
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
          <Target className="size-4" aria-hidden /> Valor real de mercado · ΣP<sub>avg</sub>
        </div>
        <Amount value={totals?.totalAvg} className="text-5xl sm:text-6xl" />
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {totals ? `${totals.itemCount} artículos tasados con Visión IA y MCP Stealth` : "Calculando…"}
        </p>
      </div>

      <div className={card}>
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
          <TrendingDown className="size-4" aria-hidden /> Liquidez inmediata · ΣP<sub>min</sub>
        </div>
        <Amount value={totals?.totalMin} className="text-3xl" />
      </div>

      <div className={card}>
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
          <TrendingUp className="size-4" aria-hidden /> Potencial máximo · ΣP<sub>max</sub>
        </div>
        <Amount value={totals?.totalMax} className="text-3xl" />
      </div>

      <div className={`${card} flex items-center gap-4 sm:col-span-2`}>
        {profile ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element -- avatar SVG embebido */}
            <img src={profile.avatarUrl} alt="" className="size-14 rounded-2xl" />
            <div className="min-w-0">
              <p className="text-lg font-semibold">{profile.name}</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {profile.role} · <MapPin className="inline size-3.5 align-[-2px]" aria-hidden /> {profile.city}
              </p>
            </div>
          </>
        ) : (
          <span className="h-14 w-full animate-pulse rounded-2xl bg-zinc-200 dark:bg-zinc-800" />
        )}
      </div>
    </section>
  );
}

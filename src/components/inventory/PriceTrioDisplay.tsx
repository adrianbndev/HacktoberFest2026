import { Target, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { formatEur } from "./format";

interface PriceTrioDisplayProps {
  priceMin: number;
  priceAvg: number;
  priceMax: number;
}

function Price({ icon: Icon, label, value, main }: { icon: LucideIcon; label: string; value: number; main?: boolean }) {
  return (
    <div className={`rounded-2xl p-3 ${main ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800"}`}>
      <p className={`flex items-center gap-1 text-[11px] font-medium ${main ? "opacity-80" : "text-zinc-500 dark:text-zinc-400"}`}>
        <Icon className="size-3.5" aria-hidden /> {label}
      </p>
      <p className={`mt-1 font-semibold tabular-nums ${main ? "text-xl" : "text-base"}`}>{formatEur(value)}</p>
    </div>
  );
}

export function PriceTrioDisplay({ priceMin, priceAvg, priceMax }: PriceTrioDisplayProps) {
  return (
    <div className="grid grid-cols-[1fr_1.3fr_1fr] items-end gap-2">
      <Price icon={TrendingDown} label="Venta rápida" value={priceMin} />
      <Price icon={Target} label="Precio medio" value={priceAvg} main />
      <Price icon={TrendingUp} label="Techo" value={priceMax} />
    </div>
  );
}

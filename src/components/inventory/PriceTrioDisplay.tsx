import { formatEur } from "./format";

interface PriceRangeProps {
  priceMin: number;
  priceAvg: number;
  priceMax: number;
}

// Horquilla de venta rápida a máximo con el precio justo marcado en su sitio real.
export function RangeRuler({ priceMin, priceAvg, priceMax, onAccent = false }: PriceRangeProps & { onAccent?: boolean }) {
  const position = priceMax > priceMin ? ((priceAvg - priceMin) / (priceMax - priceMin)) * 100 : 50;
  const muted = onAccent ? "text-on-accent-2" : "text-ink-2";
  return (
    <div>
      <div aria-hidden className={`relative h-1.5 rounded-full ${onAccent ? "bg-white/25" : "bg-fog-2"}`}>
        <span
          className={`absolute inset-y-0 left-0 rounded-full ${onAccent ? "bg-white/55" : "bg-accent/30"}`}
          style={{ width: `${position}%` }}
        />
        <span
          className={`absolute top-1/2 h-3.5 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full ${
            onAccent ? "bg-white" : "bg-accent"
          }`}
          style={{ left: `${position}%` }}
        />
      </div>
      <dl className="mt-3 flex justify-between gap-4">
        <div>
          <dt className={`text-[13px] ${muted}`}>Venta rápida</dt>
          <dd className="text-[15px] font-semibold tabular-nums">{formatEur(priceMin)}</dd>
        </div>
        <div className="text-right">
          <dt className={`text-[13px] ${muted}`}>Máximo</dt>
          <dd className="text-[15px] font-semibold tabular-nums">{formatEur(priceMax)}</dd>
        </div>
      </dl>
    </div>
  );
}

export function PriceTrioDisplay(props: PriceRangeProps) {
  return (
    <div className="flex flex-col gap-3">
      <p>
        <span className="block text-[13px] text-ink-2">Precio justo</span>
        <span className="font-display text-[2rem] font-semibold leading-tight tracking-[-0.03em] tabular-nums">
          {formatEur(props.priceAvg)}
        </span>
      </p>
      <RangeRuler {...props} />
    </div>
  );
}

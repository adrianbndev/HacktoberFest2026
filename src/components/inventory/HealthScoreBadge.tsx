import type { ConditionLabel } from "@/types/sdd";

// El nivel lo dan las 5 barras; el color solo avisa de los estados que restan valor (ámbar y rosa).
const CONDITION_TONE: Record<ConditionLabel, { chip: string; fill: string; grade: number }> = {
  Nuevo: { chip: "bg-fog-2 text-ink", fill: "bg-ink", grade: 5 },
  "Como nuevo": { chip: "bg-fog-2 text-ink", fill: "bg-ink", grade: 4 },
  "Buen estado": { chip: "bg-fog-2 text-ink", fill: "bg-ink", grade: 3 },
  "Desgaste visible": { chip: "bg-amber-50 text-amber-800", fill: "bg-amber-600", grade: 2 },
  "Para piezas": { chip: "bg-rose-50 text-rose-800", fill: "bg-rose-600", grade: 1 },
};

const GRADES = [1, 2, 3, 4, 5];

export function ConditionChip({ label }: { label: ConditionLabel }) {
  const { chip, fill, grade } = CONDITION_TONE[label];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full py-1 pl-2.5 pr-3 text-[13px] font-semibold ${chip}`}>
      <span aria-hidden className="flex gap-0.5">
        {GRADES.map((step) => (
          <span key={step} className={`h-2.5 w-1 rounded-full ${step <= grade ? fill : "bg-current opacity-20"}`} />
        ))}
      </span>
      {label}
    </span>
  );
}

interface HealthScoreBadgeProps {
  score: number;
  label: ConditionLabel;
  reasoning: string;
}

export function HealthScoreBadge({ score, label, reasoning }: HealthScoreBadgeProps) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <ConditionChip label={label} />
        <span className="text-sm tabular-nums text-ink-2">
          Estado <span className="font-semibold text-ink">{score}</span>/100
        </span>
      </div>
      <div
        role="meter"
        aria-label="Estado del producto"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-valuetext={`${label}, ${score} de 100`}
        className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-fog-2"
      >
        <div className={`h-full rounded-full ${CONDITION_TONE[label].fill}`} style={{ width: `${score}%` }} />
      </div>
      <p className="mt-2.5 text-sm leading-relaxed text-ink-2">{reasoning}</p>
    </div>
  );
}

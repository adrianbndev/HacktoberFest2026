import type { ConditionLabel } from "@/types/sdd";

interface HealthScoreBadgeProps {
  score: number;
  label: ConditionLabel;
  reasoning: string;
}

// Colores semánticos de la spec de Nivel 1: esmeralda >= 85, ámbar 60-84, coral < 60.
function tone(score: number) {
  if (score >= 85) return { bar: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" };
  if (score >= 60) return { bar: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" };
  return { bar: "bg-rose-500", text: "text-rose-600 dark:text-rose-400" };
}

export function HealthScoreBadge({ score, label, reasoning }: HealthScoreBadgeProps) {
  const { bar, text } = tone(score);
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">Salud {score}%</span>
        <span className={`font-semibold ${text}`}>{label}</span>
      </div>
      <div
        role="meter"
        aria-label="Salud del producto"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        className="mt-1.5 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
      >
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${score}%` }} />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">{reasoning}</p>
    </div>
  );
}

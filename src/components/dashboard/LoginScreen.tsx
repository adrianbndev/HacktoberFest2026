"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { ConditionChip } from "@/components/inventory/HealthScoreBadge";
import { RangeRuler } from "@/components/inventory/PriceTrioDisplay";
import { formatEur } from "@/components/inventory/format";
import { Brand } from "./Brand";
import { ThemeToggle } from "./ThemeToggle";

interface LoginScreenProps {
  onLogin: () => Promise<string | null>;
}

// Tasación de muestra para enseñar qué devuelve la app antes de entrar; va rotulada como ejemplo.
const EXAMPLE = { name: "Nintendo Switch OLED", priceMin: 205, priceAvg: 249, priceMax: 309 };

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function login() {
    setPending(true);
    setError(await onLogin());
    setPending(false);
  }

  return (
    <main className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      <section className="flex flex-col justify-between gap-14 p-6 sm:p-10 lg:p-14">
        <div className="flex items-center justify-between gap-4">
          <Brand size="lg" />
          <ThemeToggle />
        </div>
        <div className="max-w-lg">
          <h1 className="font-display text-[clamp(2.5rem,5.2vw,4rem)] font-semibold leading-[1.02] tracking-[-0.035em] text-balance">
            Tasa tus objetos con una foto.
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-ink-2">
            Haz una foto con el móvil y en segundos sabrás en qué estado está y cuánto vale en Wallapop, Vinted,
            Milanuncios y eBay.
          </p>
          <button
            type="button"
            onClick={login}
            disabled={pending}
            className="mt-9 flex h-13 items-center gap-3 rounded-full bg-ink px-7 text-base font-semibold text-paper transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {pending ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <GoogleMark />}
            Continuar con Google
          </button>
          {error && (
            <p role="alert" className="mt-4 max-w-md text-[15px] text-rose-700">
              {error}
            </p>
          )}
        </div>
        <p className="text-sm text-ink-2">Hacktoberfest 2026 · Ales, Adri y Matías</p>
      </section>

      <aside aria-label="Ejemplo de tasación" className="hidden items-center justify-center bg-accent p-14 lg:flex">
        <div className="w-full max-w-sm rounded-panel bg-paper p-7 shadow-[0_32px_64px_-24px_rgb(16_17_20/0.45)]">
          <div className="flex items-center justify-between gap-3">
            <p className="text-base font-semibold">{EXAMPLE.name}</p>
            <span className="rounded-full bg-fog px-2.5 py-1 text-[13px] font-semibold text-ink-2">Ejemplo</span>
          </div>
          <div className="mt-3">
            <ConditionChip label="Como nuevo" />
          </div>
          <p className="mt-7 text-[13px] text-ink-2">Precio justo</p>
          <p className="font-display text-5xl font-semibold tracking-[-0.035em] tabular-nums">{formatEur(EXAMPLE.priceAvg)}</p>
          <div className="mt-6">
            <RangeRuler priceMin={EXAMPLE.priceMin} priceAvg={EXAMPLE.priceAvg} priceMax={EXAMPLE.priceMax} />
          </div>
        </div>
      </aside>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5 rounded-full bg-white p-0.5" aria-hidden>
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7Z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 7.9-2.9l-3.9-3c-1.1.7-2.4 1.2-4 1.2-3.1 0-5.7-2.1-6.6-4.9h-4v3.1A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.4 14.4a7.2 7.2 0 0 1 0-4.7V6.6h-4a12 12 0 0 0 0 10.9l4-3.1Z" />
      <path fill="#EA4335" d="M12 4.8c1.7 0 3.3.6 4.5 1.8l3.4-3.4A12 12 0 0 0 1.4 6.6l4 3.1C6.3 6.9 8.9 4.8 12 4.8Z" />
    </svg>
  );
}

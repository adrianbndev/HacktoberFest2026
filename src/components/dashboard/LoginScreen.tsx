"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

interface LoginScreenProps {
  onLogin: () => Promise<string | null>;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function login() {
    setPending(true);
    setError(await onLogin());
    setPending(false);
  }

  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <div className="flex w-full max-w-sm flex-col gap-6 rounded-3xl border border-zinc-200 bg-white p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <span className="grid size-12 place-items-center rounded-2xl bg-zinc-900 text-white dark:bg-white dark:text-zinc-900">
          <Sparkles className="size-6" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-semibold">LifeOS · ReCommerce AI</h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Tasa tus objetos de segunda mano con una foto del móvil y sigue su valor en Wallapop, Vinted, Milanuncios y eBay.
          </p>
        </div>
        <button
          type="button"
          onClick={login}
          disabled={pending}
          className="flex items-center justify-center gap-3 rounded-2xl bg-zinc-900 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60 dark:bg-white dark:text-zinc-900"
        >
          {pending ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <GoogleMark />}
          Continuar con Google
        </button>
        {error && (
          <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden>
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7Z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 7.9-2.9l-3.9-3c-1.1.7-2.4 1.2-4 1.2-3.1 0-5.7-2.1-6.6-4.9h-4v3.1A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.4 14.4a7.2 7.2 0 0 1 0-4.7V6.6h-4a12 12 0 0 0 0 10.9l4-3.1Z" />
      <path fill="#EA4335" d="M12 4.8c1.7 0 3.3.6 4.5 1.8l3.4-3.4A12 12 0 0 0 1.4 6.6l4 3.1C6.3 6.9 8.9 4.8 12 4.8Z" />
    </svg>
  );
}

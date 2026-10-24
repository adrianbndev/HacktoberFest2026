"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

const STORAGE_KEY = "smartloot-theme";

function subscribe(callback: () => void) {
  const observer = new MutationObserver(() => callback());
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getSnapshot(): boolean {
  return typeof document !== "undefined" && document.documentElement.classList.contains("dark");
}

function getServerSnapshot(): boolean {
  return false;
}

// Botón de alternancia entre modo claro y oscuro con persistencia en localStorage.
export function ThemeToggle() {
  const isDark = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  function toggleTheme() {
    const nextDark = !document.documentElement.classList.contains("dark");
    if (nextDark) {
      document.documentElement.classList.add("dark");
      try {
        localStorage.setItem(STORAGE_KEY, "dark");
      } catch {
        // Ignorar restricciones en entornos con storage bloqueado
      }
    } else {
      document.documentElement.classList.remove("dark");
      try {
        localStorage.setItem(STORAGE_KEY, "light");
      } catch {
        // Ignorar restricciones en entornos con storage bloqueado
      }
    }
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      className="flex size-10 items-center justify-center rounded-full text-ink-2 transition-colors hover:bg-fog hover:text-ink focus-visible:outline-accent"
    >
      {isDark ? (
        <Sun className="size-4.5 transition-transform duration-200 hover:rotate-45" aria-hidden />
      ) : (
        <Moon className="size-4.5 transition-transform duration-200 hover:-rotate-12" aria-hidden />
      )}
    </button>
  );
}

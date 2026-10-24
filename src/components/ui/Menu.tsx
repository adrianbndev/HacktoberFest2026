"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface MenuItem {
  label: string;
  icon: LucideIcon;
  onSelect: () => void;
  danger?: boolean;
}

interface MenuProps {
  buttonLabel: string;
  buttonContent: ReactNode;
  buttonClassName: string;
  items: MenuItem[];
  heading?: ReactNode;
  placement?: "up" | "down";
}

// Botón que despliega una lista de acciones; se cierra al elegir, con Escape o al salir el foco.
export function Menu({ buttonLabel, buttonContent, buttonClassName, items, heading, placement = "down" }: MenuProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);

  return (
    <div
      className="relative"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <button
        ref={buttonRef}
        type="button"
        aria-label={buttonLabel}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className={buttonClassName}
      >
        {buttonContent}
      </button>
      {open && (
        <div
          id={panelId}
          className={`absolute right-0 z-30 w-64 rounded-inner bg-paper p-1.5 shadow-[0_12px_32px_-8px_rgb(16_17_20/0.22),0_2px_6px_rgb(16_17_20/0.06)] ring-1 ring-line ${
            placement === "up" ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          {heading && <div className="border-b border-line px-3 pb-2.5 pt-2">{heading}</div>}
          <ul className={heading ? "pt-1.5" : undefined}>
            {items.map(({ label, icon: Icon, onSelect, danger }) => (
              <li key={label}>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    // El foco vuelve al botón antes de la acción: así un diálogo que se abra lo devuelve ahí al cerrarse.
                    buttonRef.current?.focus();
                    onSelect();
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[15px] font-medium transition-colors hover:bg-fog ${
                    danger ? "text-rose-700" : "text-ink"
                  }`}
                >
                  <Icon className="size-4.5 shrink-0" aria-hidden />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

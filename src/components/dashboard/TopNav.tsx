"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, RotateCcw } from "lucide-react";
import type { UserProfile } from "@/types/sdd";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Menu } from "@/components/ui/Menu";
import { Brand } from "./Brand";

interface TopNavProps {
  profile?: UserProfile;
  onLogout: () => void;
  onResetDemo: () => void;
}

const TABS = [
  { href: "/", label: "Inicio" },
  { href: "/inventario", label: "Mi inventario" },
];

export function TopNav({ profile, onLogout, onResetDemo }: TopNavProps) {
  const pathname = usePathname();
  const [confirmReset, setConfirmReset] = useState(false);

  return (
    <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
      <Link href="/" aria-label="SmartLoot, inicio" className="rounded-lg">
        <Brand />
      </Link>

      <nav aria-label="Principal" className="order-last flex w-full rounded-full bg-fog p-1 sm:order-none sm:w-auto">
        {TABS.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex h-10 flex-1 items-center justify-center rounded-full px-5 text-[15px] font-semibold transition-colors sm:flex-none ${
                active ? "bg-paper text-accent shadow-[0_1px_3px_rgb(16_17_20/0.1)]" : "text-ink-2 hover:text-ink"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      <Menu
        buttonLabel="Tu cuenta"
        buttonClassName="flex items-center gap-2.5 rounded-full p-1 pr-1 transition-colors hover:bg-fog sm:pr-4"
        buttonContent={
          profile ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element -- foto de la cuenta de Google */}
              <img src={profile.avatarUrl} alt="" referrerPolicy="no-referrer" className="size-9 rounded-full bg-fog" />
              <span className="hidden text-[15px] font-semibold sm:inline">{profile.name.split(" ")[0]}</span>
            </>
          ) : (
            <span className="block size-9 animate-pulse rounded-full bg-fog" />
          )
        }
        heading={
          profile && (
            <>
              <p className="font-semibold">{profile.name}</p>
              {profile.email && <p className="truncate text-sm text-ink-2">{profile.email}</p>}
            </>
          )
        }
        items={[
          { label: "Restaurar productos de demo", icon: RotateCcw, onSelect: () => setConfirmReset(true) },
          { label: "Salir", icon: LogOut, onSelect: onLogout },
        ]}
      />

      <ConfirmDialog
        open={confirmReset}
        title="¿Restaurar los productos de demo?"
        body="Tu inventario volverá a tener solo los 3 productos de ejemplo. Lo que hayas tasado se borrará."
        confirmLabel="Restaurar"
        onConfirm={() => {
          setConfirmReset(false);
          onResetDemo();
        }}
        onCancel={() => setConfirmReset(false)}
      />
    </header>
  );
}

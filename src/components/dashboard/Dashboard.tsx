"use client";

import { useState } from "react";
import { ServerCrash } from "lucide-react";
import { InventoryGrid } from "@/components/inventory/InventoryGrid";
import { MobileSyncModal } from "@/components/mobile-sync/MobileSyncModal";
import { LoginScreen } from "./LoginScreen";
import { PatrimonyBentoHeader } from "./PatrimonyBentoHeader";
import { TopNav } from "./TopNav";
import { useDashboardState } from "./useDashboardState";

export function Dashboard() {
  const { user, inventory, loadingInventory, error, login, logout, reloadInventory } = useDashboardState();
  const [mobileSyncOpen, setMobileSyncOpen] = useState(false);

  if (user === undefined) return <main className="min-h-dvh" aria-busy />; // comprobando la sesión guardada
  if (user === null) return <LoginScreen onLogin={login} />;

  const current = loadingInventory ? undefined : inventory ?? undefined;
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-6 sm:px-6 lg:py-10">
      <TopNav profile={current?.profile} onLogout={logout} />
      {error ? (
        <div role="alert" className="flex items-center gap-3 rounded-3xl border border-rose-200 bg-rose-50 p-6 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
          <ServerCrash className="size-6 shrink-0" aria-hidden />
          <p>{error}</p>
        </div>
      ) : (
        <>
          <PatrimonyBentoHeader
            profile={current?.profile}
            totals={current?.totals}
            onAddWithMobile={() => setMobileSyncOpen(true)}
          />
          <InventoryGrid items={current?.items} loading={loadingInventory} />
          <MobileSyncModal
            userId={user.uid}
            isOpen={mobileSyncOpen}
            onClose={() => setMobileSyncOpen(false)}
            onItemCreated={reloadInventory}
          />
        </>
      )}
    </main>
  );
}

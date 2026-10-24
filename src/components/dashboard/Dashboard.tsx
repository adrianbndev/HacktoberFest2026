"use client";

import { useState } from "react";
import { ServerCrash } from "lucide-react";
import { InventoryGrid } from "@/components/inventory/InventoryGrid";
import { MobileSyncModal } from "@/components/mobile-sync/MobileSyncModal";
import { PatrimonyBentoHeader } from "./PatrimonyBentoHeader";
import { TopNavProfileSwitcher } from "./TopNavProfileSwitcher";
import { useDashboardState } from "./useDashboardState";

export function Dashboard() {
  const { session, userId, inventory, loadingInventory, error, switchUser, reloadInventory } = useDashboardState();
  const [mobileSyncOpen, setMobileSyncOpen] = useState(false);
  const current = loadingInventory ? undefined : inventory ?? undefined;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-6 sm:px-6 lg:py-10">
      <TopNavProfileSwitcher profiles={session?.profiles ?? []} activeUserId={userId} onSwitch={switchUser} />
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
          <InventoryGrid items={inventory?.items} loading={loadingInventory} />
          {userId && (
            <MobileSyncModal
              userId={userId}
              isOpen={mobileSyncOpen}
              onClose={() => setMobileSyncOpen(false)}
              onItemCreated={reloadInventory}
            />
          )}
        </>
      )}
    </main>
  );
}

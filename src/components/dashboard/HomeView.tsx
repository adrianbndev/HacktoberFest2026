"use client";

import { BalancePanel } from "./BalancePanel";
import { useDashboard } from "./DashboardShell";
import { InventoryByStatus } from "./InventoryByStatus";
import { RecentValuations } from "./RecentValuations";

export function HomeView() {
  const { inventory, loadingInventory, openCapture, lastAddedId } = useDashboard();
  const current = loadingInventory ? undefined : inventory ?? undefined;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,1fr)] lg:gap-5">
      <BalancePanel totals={current?.totals} onCapture={openCapture} />
      <div className="flex flex-col gap-4 lg:gap-5">
        <RecentValuations items={current?.items} lastAddedId={lastAddedId} onCapture={openCapture} />
        <InventoryByStatus items={current?.items} />
      </div>
    </div>
  );
}

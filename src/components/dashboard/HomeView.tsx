"use client";

import { BalancePanel } from "./BalancePanel";
import { useDashboard } from "./DashboardShell";
import { InventoryByStatus } from "./InventoryByStatus";
import { PlatformValue } from "./PlatformValue";
import { RecentValuations } from "./RecentValuations";

export function HomeView() {
  const { inventory, loadingInventory, openCapture, lastAddedId } = useDashboard();
  const current = loadingInventory ? undefined : inventory ?? undefined;

  // Dos filas en escritorio: saldo + movimientos, y debajo dónde vale más + por estado.
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-5">
      <div className="lg:col-span-7">
        <BalancePanel totals={current?.totals} onCapture={openCapture} />
      </div>
      <div className="lg:col-span-5">
        <RecentValuations items={current?.items} lastAddedId={lastAddedId} onCapture={openCapture} />
      </div>
      <div className="lg:col-span-7">
        <PlatformValue items={current?.items} />
      </div>
      <div className="lg:col-span-5">
        <InventoryByStatus items={current?.items} />
      </div>
    </div>
  );
}
